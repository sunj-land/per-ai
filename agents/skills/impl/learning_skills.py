import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from core.skill import Skill
from core.llm import llm_service
import logging

logger = logging.getLogger(__name__)

class GoalDecompositionSkill(Skill):
    """
    Parses a natural language goal into structured data (type, deadline, current level, daily hours).
    """
    def __init__(self):
        super().__init__(
            name="goal_decomposition",
            description="Extracts structured goal info from natural language input.",
            input_schema={"type": "object", "properties": {"goal_text": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"goal_type": {"type": "string"}, "deadline_date": {"type": "string"}, "daily_hours": {"type": "number"}, "current_level": {"type": "string"}}}
        )

    async def execute(self, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        goal_text = inputs.get("goal_text")
        if not goal_text:
            raise ValueError("Missing 'goal_text' in inputs")

        prompt = f"""
        Analyze the following learning goal and extract key information into JSON format:
        Goal: "{goal_text}"

        Required JSON fields:
        - goal_type: (e.g., "language", "programming", "exam", "hobby")
        - deadline_date: (YYYY-MM-DD format based on context, assume today is {datetime.now().strftime('%Y-%m-%d')}. If duration is given like '3 months', calculate date.)
        - daily_hours: (Estimated daily study hours user can commit, default to 1.0 if not specified)
        - current_level: (User's current proficiency if mentioned, else "beginner")

        Return ONLY the JSON object.
        """

        try:
            response = await llm_service.chat([{"role": "user", "content": prompt}], json_mode=False)
            logger.info(f"GoalDecompositionSkill raw response: {response}")

            if not response or not str(response).strip():
                raise ValueError("Empty response from LLM")

            # Extract JSON from response
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find something that looks like a JSON object
                json_match = re.search(r'(\{.*?\})', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response

            data = json.loads(json_str)
            return data
        except TimeoutError as e:
            logger.error(f"Goal decomposition timeout: {e}")
            raise RuntimeError("大模型调用超时") from e
        except Exception as e:
            logger.error(f"Goal decomposition failed: {e}")
            # Fallback
            return {
                "goal_type": "general",
                "deadline_date": (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                "daily_hours": 1.0,
                "current_level": "beginner"
            }

class PlanGenerationSkill(Skill):
    """
    Generates a structured learning plan with milestones and tasks based on goal info.
    """
    def __init__(self):
        super().__init__(
            name="plan_generation",
            description="Generates milestones and tasks for a given goal.",
            input_schema={"type": "object", "properties": {"goal_info": {"type": "object"}}},
            output_schema={"type": "object", "properties": {"milestones": {"type": "array"}}}
        )

    async def execute(self, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        goal_info = inputs.get("goal_info")
        if not goal_info:
            raise ValueError("Missing 'goal_info'")

        prompt = f"""
        Create a detailed learning plan for the following goal:
        {json.dumps(goal_info, indent=2)}

        The plan should be broken down into Milestones, and each Milestone into specific Tasks.

        Output Format (JSON):
        {{
            "estimated_total_hours": <number>,
            "difficulty_coef": <float 0.1-1.0>,
            "milestones": [
                {{
                    "title": "<Milestone Title>",
                    "deadline": "<YYYY-MM-DD>",
                    "tasks": [
                        {{
                            "title": "<Task Title>",
                            "type": "<video|exercise|reading|summary|other>",
                            "estimated_min": <number>,
                            "description": "<Short description>"
                        }},
                        ...
                    ]
                }},
                ...
            ]
        }}

        Ensure the plan fits the deadline and daily hours constraints.
        Return ONLY valid JSON.
        """

        try:
            response = await llm_service.chat([{"role": "user", "content": prompt}], json_mode=False)
            logger.info(f"PlanGenerationSkill raw response: {response}")

            if not response or not str(response).strip():
                raise ValueError("Empty response from LLM")

            # Extract JSON from response
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find something that looks like a JSON object
                json_match = re.search(r'(\{.*?\})', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response

            data = json.loads(json_str)
            return data
        except TimeoutError as e:
            logger.error(f"Plan generation timeout: {e}")
            raise RuntimeError("大模型调用超时") from e
        except Exception as e:
            logger.error(f"Plan generation failed: {e}")
            # Provide a fallback plan if generation fails
            return {
                "estimated_total_hours": 10.0,
                "difficulty_coef": 0.5,
                "milestones": [
                    {
                        "title": "初始阶段",
                        "deadline": goal_info.get("deadline_date", (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')),
                        "tasks": [
                            {
                                "title": "了解基础概念",
                                "type": "reading",
                                "estimated_min": 60,
                                "description": f"开始关于 {goal_info.get('goal_type', '学习目标')} 的基础学习"
                            }
                        ]
                    }
                ]
            }
