import asyncio

from app.services.skill_install_progress_service import SkillInstallProgressService
from app.services.skill_service import SkillService


def test_build_idempotency_key_stable():
    service = SkillService()
    key1 = service._build_idempotency_key("weather", "1.0.0", "install")
    key2 = service._build_idempotency_key("weather", "1.0.0", "install")
    key3 = service._build_idempotency_key("weather", "1.0.1", "install")
    assert key1 == key2
    assert key1 != key3


def test_version_sorting():
    service = SkillService()
    values = ["1.0.2", "1.0.10", "0.9.9"]
    sorted_values = sorted(values, key=service._version_tuple, reverse=True)
    assert sorted_values[0] == "1.0.10"


def test_progress_service_publish_and_snapshot():
    progress = SkillInstallProgressService()
    task_id = "task-001"
    progress.create_task(task_id)
    asyncio.run(progress.publish(task_id, "running", 20, "step-1"))
    snap = progress.snapshot(task_id)
    assert snap["status"] == "running"
    assert snap["progress"] == 20
    assert len(snap["logs"]) == 1


def test_progress_service_stream_finish():
    progress = SkillInstallProgressService()
    task_id = "task-002"
    progress.create_task(task_id)

    async def produce():
        await progress.publish(task_id, "running", 30, "running")
        await progress.publish(task_id, "success", 100, "done")

    asyncio.run(produce())

    async def consume():
        events = []
        async for event in progress.stream(task_id):
            events.append(event)
            if event["status"] == "success":
                break
        return events

    collected = asyncio.run(consume())
    assert collected[-1]["status"] == "success"
