"""
本文件用于对比迁移前后编排输出并生成 diff 报告 维护者 SunJie 创建于 2026-03-15 最近修改于 2026-03-15
"""

import asyncio
import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from core.protocol import AgentRequest, AgentResponse
from core.manager import AgentGraphRuntime, build_collaboration_graph, build_master_graph


@dataclass
class ValidationCase:
    """
    描述迁移验证单个用例
    """

    name: str
    request: AgentRequest


class FakeBackendClient:
    """
    提供可预测的 completion 响应以保证迁移对比稳定
    """

    async def completion(self, payload):
        user_text = payload.messages[-1].content.lower()
        if "intent classifier" in user_text:
            if "search" in user_text or "find" in user_text:
                return type("Resp", (), {"content": '{"intent":"SEARCH_ARTICLES","confidence":0.9}'})()
            return type("Resp", (), {"content": '{"intent":"GENERAL_CHAT","confidence":0.8}'})()
        return type("Resp", (), {"content": "stubbed-answer"})()


class FakeArticleAgent:
    """
    提供可预测的检索结果用于迁移对比
    """

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        query = task.get("query", "")
        return {
            "count": 1,
            "articles": [{"id": "a1", "content": f"article for {query}"}],
            "summary": "stub-summary",
        }


def _legacy_emulation(runtime: AgentGraphRuntime, request: AgentRequest) -> Dict[str, Any]:
    """
    模拟迁移前顺序编排执行 作为对照基线
    """

    async def _run() -> Dict[str, Any]:
        intent_result = await runtime.classify_intent(request.query)
        if intent_result.get("intent") == "SEARCH_ARTICLES":
            article_results = await runtime.search_articles(request.query)
            response = await runtime.response_generator_node(
                {
                    "request": request,
                    "intent": intent_result.get("intent"),
                    "intent_confidence": intent_result.get("confidence", 0.0),
                    "article_results": article_results,
                    "final_response": None,
                    "messages": [],
                    "error": None,
                }
            )
            final_answer = response.get("final_response")
        else:
            chat_response = await runtime.general_chat_node(
                {
                    "request": request,
                    "intent": intent_result.get("intent"),
                    "intent_confidence": intent_result.get("confidence", 0.0),
                    "article_results": None,
                    "final_response": None,
                    "messages": [],
                    "error": None,
                }
            )
            article_results = None
            final_answer = chat_response.get("final_response")
        return AgentResponse(
            answer=final_answer or "No response generated.",
            source_agent="article_agent" if intent_result.get("intent") == "SEARCH_ARTICLES" else "general_llm",
            latency_ms=0.0,
            metadata={
                "intent": intent_result.get("intent"),
                "confidence": intent_result.get("confidence", 0.0),
                "article_count": article_results.get("count", 0) if article_results else 0,
            },
            error=None,
        ).model_dump(mode="json")

    return asyncio.run(_run())


def _graph_execution(runtime: AgentGraphRuntime, request: AgentRequest) -> Dict[str, Any]:
    """
    执行迁移后图编排并映射到标准协议
    """

    async def _run() -> Dict[str, Any]:
        graph = build_master_graph(runtime)
        state = await graph.ainvoke(
            {
                "request": request,
                "intent": None,
                "intent_confidence": 0.0,
                "article_results": None,
                "final_response": None,
                "messages": [],
                "error": None,
            }
        )
        return AgentResponse(
            answer=state.get("final_response", "No response generated."),
            source_agent="article_agent" if state.get("intent") == "SEARCH_ARTICLES" else "general_llm",
            latency_ms=0.0,
            metadata={
                "intent": state.get("intent"),
                "confidence": state.get("intent_confidence"),
                "article_count": state.get("article_results", {}).get("count", 0) if state.get("article_results") else 0,
            },
            error=state.get("error"),
        ).model_dump(mode="json")

    return asyncio.run(_run())


def _collaboration_emulation(runtime: AgentGraphRuntime, task: str) -> Dict[str, Any]:
    """
    模拟迁移前协作顺序执行 作为对照基线
    """

    async def _run() -> Dict[str, Any]:
        state: Dict[str, Any] = {
            "task": task,
            "plan": [],
            "current_step": 0,
            "results": {},
            "messages": [],
            "final_response": "",
        }
        state.update(await runtime.plan_node(state))
        while True:
            route = runtime.route_next_step(state)
            if route == "aggregator":
                state.update(await runtime.aggregator_node(state))
                break
            if route == "text":
                state.update(await runtime.text_agent_node(state))
            elif route == "data":
                state.update(await runtime.data_agent_node(state))
            elif route == "image":
                state.update(await runtime.image_agent_node(state))
        return state

    return asyncio.run(_run())


def _collaboration_graph(runtime: AgentGraphRuntime, task: str) -> Dict[str, Any]:
    """
    执行迁移后协作图编排并返回结束态
    """

    async def _run() -> Dict[str, Any]:
        graph = build_collaboration_graph(runtime)
        return await graph.ainvoke(
            {
                "task": task,
                "plan": [],
                "current_step": 0,
                "results": {},
                "messages": [],
                "final_response": "",
            }
        )

    return asyncio.run(_run())


def _build_diff(expected: Dict[str, Any], actual: Dict[str, Any]) -> List[str]:
    """
    对比两个 JSON 结构并生成统一 diff 文本
    """

    expected_text = json.dumps(expected, ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    actual_text = json.dumps(actual, ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    return list(
        difflib.unified_diff(
            expected_text,
            actual_text,
            fromfile="legacy",
            tofile="langgraph",
            lineterm="",
        )
    )


def main() -> None:
    """
    执行迁移验证并输出 diff 报告
    """

    runtime = AgentGraphRuntime(backend_client=FakeBackendClient(), article_agent=FakeArticleAgent())
    cases = [
        ValidationCase(name="search_case", request=AgentRequest(query="search python best practice")),
        ValidationCase(name="chat_case", request=AgentRequest(query="hello there")),
    ]
    report: Dict[str, Any] = {"master_graph": [], "collaboration_graph": [], "zero_diff": True}
    for case in cases:
        expected = _legacy_emulation(runtime, case.request)
        actual = _graph_execution(runtime, case.request)
        diff_lines = _build_diff(expected, actual)
        report["master_graph"].append(
            {
                "case": case.name,
                "expected": expected,
                "actual": actual,
                "diff": diff_lines,
                "passed": len(diff_lines) == 0,
            }
        )
        if diff_lines:
            report["zero_diff"] = False
    collaboration_task = "summarize text then analyze data"
    expected_collab = _collaboration_emulation(runtime, collaboration_task)
    actual_collab = _collaboration_graph(runtime, collaboration_task)
    collab_diff = _build_diff(expected_collab, actual_collab)
    report["collaboration_graph"].append(
        {
            "case": "collaboration_case",
            "expected": expected_collab,
            "actual": actual_collab,
            "diff": collab_diff,
            "passed": len(collab_diff) == 0,
        }
    )
    if collab_diff:
        report["zero_diff"] = False
    report_path = Path(__file__).resolve().parent / "migration_diff_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report_path": str(report_path), "zero_diff": report["zero_diff"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
