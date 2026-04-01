# Comprehensive Demo Agent

本示例项目提供了一个完整的 LangGraph Agent 实现，展示了 LangGraph 的核心概念与高级功能。

## 核心功能与架构演示

1. **项目结构清晰**:
   - `graph.py`: 定义 LangGraph 状态图与节点逻辑。
   - `state.py`: 基于 `TypedDict` 和 `Annotated` 定义短期记忆和额外状态。
   - `tools.py`: 定义三个实用工具（网络搜索、计算器、文件操作）。
   - `llm_adapter.py`: `LiteLLMProvider` 与 LangChain 消息格式的桥接适配器。

2. **LiteLLMProvider (DeepSeek 集成)**:
   - 所有模型调用均通过 `providers.litellm_provider.LiteLLMProvider` 完成。
   - 配置为使用 `deepseek/deepseek-chat` 模型，自带错误重试和回调支持。

3. **Memory 记忆系统**:
   - **短期记忆**: 包含在状态图的 `messages` 中，用于维系多轮会话上下文。
   - **长期记忆**: 提供 `long_term_memory` 状态字段用于传递跨会话数据和偏好。
   - **持久化**: 使用 `MemorySaver` 进行 Checkpoint，实现状态的持久化和检索。

4. **Interrupts 中断机制**:
   - 工作流被配置为在 `human_review` 节点前触发中断 (`interrupt_before=["human_review"]`)。
   - 当模型决定执行高风险操作（如 `file_operation(write)`）时，代理将挂起执行等待人类审核确认。

5. **Streaming 流式与并发支持**:
   - Agent 支持通过 LangGraph 原生的 Stream 方法以 `stream_mode="values"` 或 `"updates"` 实时输出。
   - （请参考全局 API 的 `/runs/stream` 端点实现并发调用）。

## API 参考

### 1. 本地调用示例
```python
import asyncio
from agents.agents.comprehensive_demo_agent.graph import ComprehensiveDemoAgent

async def main():
    agent = ComprehensiveDemoAgent()
    # 非流式调用
    result = await agent.process_task({
        "query": "计算 1024 乘以 4，然后将结果写入 result.txt",
        "thread_id": "session_01"
    })
    print(result)

    # 针对流式事件
    config = {"configurable": {"thread_id": "session_01"}}
    async for event in agent.workflow.astream({"messages": [("user", "你好")]}, config=config, stream_mode="values"):
        print(event)

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. 人工中断 (Human in the loop) 恢复示例
当代理在写入文件前挂起时，客户端可注入用户的批准决定并恢复执行：
```python
# 获取当前挂起的状态
state = agent.workflow.get_state(config)
if state.next == ("human_review",):
    # 批准并继续执行
    await agent.workflow.ainvoke(None, config=config)
```

## 错误处理与日志
所有的节点内部都有异常捕获（如 `_call_model`、`_call_tools`）。遇到调用失败或参数错误时，代理不会崩溃，而是会将错误记录到 `error` 状态并优雅结束，或将工具报错作为 `ToolMessage` 传回给 LLM 重新生成策略。

## 测试覆盖
使用 `pytest` 进行集成测试，覆盖了所有的分支（意图、工具、中断等）。运行测试：
```bash
pytest tests/test_comprehensive_demo_agent.py
```
