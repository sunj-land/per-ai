from typing import Any, Dict, List, Optional
from core.skill import Skill
from app.services.schedule_service import schedule_service
from app.models.schedule import ScheduleCreate, ScheduleUpdate, ScheduleReminderCreate
from datetime import datetime
from uuid import UUID
import json

class ScheduleQuerySkill(Skill):
    def __init__(self):
        super().__init__(
            name="ScheduleQuerySkill",
            description="Query schedules based on time range and keyword.",
            input_schema={
                "start_time": "string (ISO 8601, optional)",
                "end_time": "string (ISO 8601, optional)",
                "keyword": "string (optional, search in title and description)",
                "limit": "integer (optional, default 10)"
            },
            output_schema={
                "schedules": "list of schedule objects"
            }
        )

    async def execute(self, inputs: Any, **kwargs) -> Any:
        start_time_str = inputs.get("start_time")
        end_time_str = inputs.get("end_time")
        keyword = inputs.get("keyword")
        limit = inputs.get("limit", 10)

        start_time = None
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
            except ValueError:
                pass

        end_time = None
        if end_time_str:
            try:
                end_time = datetime.fromisoformat(end_time_str)
            except ValueError:
                pass

        schedules = await schedule_service.get_schedules(start_time, end_time, keyword, limit)
        # Convert to dict manually or use jsonable_encoder if available
        # Here we use .dict() method from SQLModel
        return {"schedules": [s.dict() for s in schedules]}

class ScheduleCreateSkill(Skill):
    def __init__(self):
        super().__init__(
            name="ScheduleCreateSkill",
            description="Create a new schedule.",
            input_schema={
                "title": "string (required)",
                "description": "string (optional)",
                "start_time": "string (ISO 8601, required)",
                "end_time": "string (ISO 8601, optional)",
                "priority": "string (high/medium/low, optional)",
                "reminders": "list of reminder objects (optional)"
            },
            output_schema={
                "schedule": "created schedule object"
            }
        )

    async def execute(self, inputs: Any, **kwargs) -> Any:
        try:
            # Pydantic should handle conversion from dict
            schedule_data = ScheduleCreate.model_validate(inputs)
            schedule = await schedule_service.create_schedule(schedule_data)
            return {"schedule": schedule.dict()}
        except Exception as e:
            return {"error": str(e)}

class ScheduleUpdateSkill(Skill):
    def __init__(self):
        super().__init__(
            name="ScheduleUpdateSkill",
            description="Update an existing schedule.",
            input_schema={
                "schedule_id": "string (UUID, required)",
                "title": "string (optional)",
                "description": "string (optional)",
                "start_time": "string (ISO 8601, optional)",
                "end_time": "string (ISO 8601, optional)",
                "priority": "string (optional)",
                "reminders": "list (optional)"
            },
            output_schema={
                "schedule": "updated schedule object"
            }
        )

    async def execute(self, inputs: Any, **kwargs) -> Any:
        schedule_id_str = inputs.get("schedule_id")
        if not schedule_id_str:
            return {"error": "schedule_id is required"}

        try:
            schedule_id = UUID(schedule_id_str)
            # Remove schedule_id from update data
            update_data = {k: v for k, v in inputs.items() if k != "schedule_id"}

            schedule_in = ScheduleUpdate.model_validate(update_data)
            schedule = await schedule_service.update_schedule(schedule_id, schedule_in)

            if schedule:
                return {"schedule": schedule.dict()}
            return {"error": "Schedule not found"}
        except Exception as e:
            return {"error": str(e)}

class ScheduleDeleteSkill(Skill):
    def __init__(self):
        super().__init__(
            name="ScheduleDeleteSkill",
            description="Delete a schedule.",
            input_schema={
                "schedule_id": "string (UUID, required)"
            },
            output_schema={
                "status": "success or error message"
            }
        )

    async def execute(self, inputs: Any, **kwargs) -> Any:
        schedule_id_str = inputs.get("schedule_id")
        if not schedule_id_str:
            return {"error": "schedule_id is required"}

        try:
            schedule_id = UUID(schedule_id_str)
            success = await schedule_service.delete_schedule(schedule_id)
            if success:
                return {"status": "success"}
            return {"error": "Schedule not found"}
        except Exception as e:
            return {"error": str(e)}
