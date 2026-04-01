import asyncio
from datetime import datetime
from typing import Any, AsyncGenerator, Dict


class SkillInstallProgressService:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self, task_id: str):
        self.tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "logs": [],
            "updated_at": datetime.utcnow().isoformat(),
            "queue": asyncio.Queue(),
        }

    async def publish(self, task_id: str, status: str, progress: int, message: str):
        task = self.tasks.get(task_id)
        if not task:
            self.create_task(task_id)
            task = self.tasks[task_id]
        task["status"] = status
        task["progress"] = progress
        task["updated_at"] = datetime.utcnow().isoformat()
        event = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": task["updated_at"],
        }
        task["logs"].append(event)
        if len(task["logs"]) > 500:
            task["logs"] = task["logs"][-500:]
        await task["queue"].put(event)

    def snapshot(self, task_id: str) -> Dict[str, Any]:
        task = self.tasks.get(task_id)
        if not task:
            return {"task_id": task_id, "status": "not_found", "progress": 0, "logs": []}
        return {
            "task_id": task_id,
            "status": task["status"],
            "progress": task["progress"],
            "logs": task["logs"][-100:],
            "updated_at": task["updated_at"],
        }

    async def stream(self, task_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        task = self.tasks.get(task_id)
        if not task:
            self.create_task(task_id)
            task = self.tasks[task_id]
        for event in task["logs"][-20:]:
            yield event
        while True:
            event = await task["queue"].get()
            yield event
            if event["status"] in {"success", "failed"}:
                break


skill_install_progress_service = SkillInstallProgressService()
