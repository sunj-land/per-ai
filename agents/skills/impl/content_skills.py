import json
from typing import Dict, Any, List
import random
import logging
from core.skill import Skill
from core.llm import llm_service

logger = logging.getLogger(__name__)

class VideoGenerationSkill(Skill):
    def __init__(self):
        super().__init__(
            name="video_generation",
            description="Mocks video content generation.",
            input_schema={"type": "object", "properties": {"task_title": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"url": {"type": "string"}}}
        )

    async def execute(self, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        task_title = inputs.get("task_title", "General Task")
        
        # Mock Video URLs
        mock_videos = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ", # Rick Roll (Classic)
            "https://www.youtube.com/watch?v=9bZkp7q19f0", # Gangnam Style
            "https://www.youtube.com/watch?v=fJ9rUzIMcZQ", # Queen - Bohemian Rhapsody
        ]
        
        url = random.choice(mock_videos)
        
        return {
            "content_type": "video",
            "title": f"Video Lesson: {task_title}",
            "url": url,
            "duration_sec": random.randint(300, 1800), # 5-30 mins
            "difficulty": 0.5,
            "metadata": {"source": "mock_youtube"}
        }

class ExerciseGenerationSkill(Skill):
    def __init__(self):
        super().__init__(
            name="exercise_generation",
            description="Generates a quiz or exercise based on task.",
            input_schema={"type": "object", "properties": {"task_title": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"text": {"type": "string"}}}
        )

    async def execute(self, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        task_title = inputs.get("task_title", "Exercise")
        
        prompt = f"""
        Create a short multiple-choice quiz (3 questions) for the topic: "{task_title}".
        Format as JSON:
        {{
            "title": "Quiz on {task_title}",
            "questions": [
                {{
                    "question": "...",
                    "options": ["A...", "B...", "C...", "D..."],
                    "answer": "A"
                }}
            ]
        }}
        """
        
        try:
            response = llm_service.chat([{"role": "user", "content": prompt}], json_mode=True)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
                
            quiz_data = json.loads(response)
            
            return {
                "content_type": "quiz",
                "title": quiz_data.get("title", f"Quiz: {task_title}"),
                "text": json.dumps(quiz_data), # Store JSON structure in text field
                "difficulty": 0.6,
                "metadata": {"question_count": len(quiz_data.get("questions", []))}
            }
        except Exception as e:
            logger.error(f"Quiz generation failed: {e}")
            return {
                "content_type": "quiz",
                "title": f"Quiz: {task_title}",
                "text": json.dumps({"questions": [{"question": "Placeholder Question?", "options": ["A", "B"], "answer": "A"}]}),
                "difficulty": 0.1
            }

class SummaryGenerationSkill(Skill):
    def __init__(self):
        super().__init__(
            name="summary_generation",
            description="Generates a summary/reading material.",
            input_schema={"type": "object", "properties": {"task_title": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"text": {"type": "string"}}}
        )

    async def execute(self, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        task_title = inputs.get("task_title", "Topic")
        
        prompt = f"""
        Write a concise educational summary (approx 300 words) about: "{task_title}".
        Focus on key concepts and definitions.
        Format as Markdown.
        """
        
        try:
            summary = llm_service.chat([{"role": "user", "content": prompt}], json_mode=False)
            
            return {
                "content_type": "text",
                "title": f"Summary: {task_title}",
                "text": summary,
                "difficulty": 0.4,
                "metadata": {"word_count": len(summary.split())}
            }
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return {
                "content_type": "text",
                "title": f"Summary: {task_title}",
                "text": "Failed to generate summary content.",
                "difficulty": 0.0
            }
