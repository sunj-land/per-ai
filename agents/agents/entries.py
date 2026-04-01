"""
LangGraph entry points — each variable is a compiled graph consumed by langgraph.json.

Graphs are built via standalone functions so they can be tested or composed
independently of the agent class wrappers.
"""

import os

# ── Image ────────────────────────────────────────────────────────────────────
from agents.image_agent.graph import build_image_agent_graph, ImageAgent
from skills.impl.image_skills import ImagePreprocessingSkill, FeatureExtractionSkill, ObjectDetectionSkill

_image_skills = {
    s.name: s
    for s in [ImagePreprocessingSkill(), FeatureExtractionSkill(), ObjectDetectionSkill()]
}
image_agent_graph = build_image_agent_graph(_image_skills)

# ── Content generator ────────────────────────────────────────────────────────
from agents.content_generator_agent.graph import build_content_generator_graph
from skills.impl.content_skills import VideoGenerationSkill, ExerciseGenerationSkill, SummaryGenerationSkill

_content_skills = {
    s.name: s
    for s in [VideoGenerationSkill(), ExerciseGenerationSkill(), SummaryGenerationSkill()]
}
content_generator_agent_graph = build_content_generator_graph(_content_skills)

# ── System expert ─────────────────────────────────────────────────────────────
from agents.system_expert_agent.graph import build_system_expert_graph
from agents.system_expert_agent.tools import KnowledgeBaseTool
from core.llm import LLMService

system_expert_agent_graph = build_system_expert_graph(
    kb_tool=KnowledgeBaseTool(),
    llm=LLMService(),
)

# ── Workflow ──────────────────────────────────────────────────────────────────
from agents.workflow_agent.graph import build_workflow_agent_graph
from skills.impl.workflow_skills import TaskDecompositionSkill, DependencyManagementSkill, ParallelExecutionSkill

_workflow_skills = {
    s.name: s
    for s in [TaskDecompositionSkill(), DependencyManagementSkill(), ParallelExecutionSkill()]
}
workflow_agent_graph = build_workflow_agent_graph(_workflow_skills)

# ── Comprehensive demo ────────────────────────────────────────────────────────
from agents.comprehensive_demo_agent.graph import build_comprehensive_demo_graph
from agents.comprehensive_demo_agent.tools import TOOLS
from providers.litellm_provider import LiteLLMProvider

_api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
_tools_schema = [
    {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": (
                tool.args_schema.model_json_schema()
                if tool.args_schema
                else {"type": "object", "properties": {}}
            ),
        },
    }
    for tool in TOOLS
]
comprehensive_demo_agent_graph = build_comprehensive_demo_graph(
    llm_provider=LiteLLMProvider(default_model="dashscope/deepseek-r1", api_key=_api_key),
    tools_schema=_tools_schema,
    tools_map={tool.name: tool for tool in TOOLS},
)

# ── Data ──────────────────────────────────────────────────────────────────────
from agents.data_agent.graph import build_data_agent_graph
from skills.impl.data_skills import DataCleaningSkill, StatisticalAnalysisSkill, DataVisualizationSkill

_data_skills = {
    s.name: s
    for s in [DataCleaningSkill(), StatisticalAnalysisSkill(), DataVisualizationSkill()]
}
data_agent_graph = build_data_agent_graph(_data_skills)

# ── Text ──────────────────────────────────────────────────────────────────────
from agents.text_agent.graph import build_text_agent_graph
from skills.impl.text_skills import TextClassificationSkill, SentimentAnalysisSkill, SummarizationSkill

_text_skills = {
    s.name: s
    for s in [TextClassificationSkill(), SentimentAnalysisSkill(), SummarizationSkill()]
}
text_agent_graph = build_text_agent_graph(_text_skills)

# ── RSS quality ───────────────────────────────────────────────────────────────
from agents.rss_quality_agent.graph import build_rss_quality_agent_graph
from agents.rss_quality_agent.tools import RSSQualityScoringTool

rss_quality_agent_graph = build_rss_quality_agent_graph(RSSQualityScoringTool())

# ── Article ───────────────────────────────────────────────────────────────────
from agents.article_agent.graph import build_article_agent_graph
from tools.article_search import ArticleSearchTool

article_agent_graph = build_article_agent_graph(ArticleSearchTool())

# ── Learning planner ──────────────────────────────────────────────────────────
from agents.learning_planner_agent.graph import build_learning_planner_graph
from skills.impl.learning_skills import GoalDecompositionSkill, PlanGenerationSkill

_learning_skills = {s.name: s for s in [GoalDecompositionSkill(), PlanGenerationSkill()]}
learning_planner_agent_graph = build_learning_planner_graph(_learning_skills)

# ── Shell risk ────────────────────────────────────────────────────────────────
from agents.shell_risk_agent.graph import build_shell_risk_agent_graph
from agents.shell_risk_agent.tools import ShellRiskEngine, ShellExecutionTool

shell_risk_agent_graph = build_shell_risk_agent_graph(ShellRiskEngine(), ShellExecutionTool())

# ── Skill caller (internal demo, not in langgraph.json) ───────────────────────
from agents.skill_caller_agent.graph import build_skill_caller_graph
from agents.skill_caller_agent.skills import SubAgentSkill

_skill_caller_skills = {"SubAgentSkill": SubAgentSkill()}
skill_caller_agent_graph = build_skill_caller_graph(_skill_caller_skills)
