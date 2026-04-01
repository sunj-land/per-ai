import logging
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.core.database import engine
from app.models.plan import PlanTask, PlanMilestone, PlanHeader, TaskStatus
from app.models.content import ContentRepo, ContentType
from app.services.agent_client import agent_client

logger = logging.getLogger(__name__)

class LearningSchedulerService:
    async def generate_daily_content(self):
        """
        Scans for pending tasks scheduled for today/tomorrow and generates content.
        """
        logger.info("Starting daily content generation job...")
        with Session(engine) as session:
            # logic: find tasks that are part of active plans, pending status, and ideally near deadline or just next in sequence
            # For simplicity: Find first 5 pending tasks for each active plan
            
            active_plans = session.exec(select(PlanHeader).where(PlanHeader.status == "active")).all()
            
            for plan in active_plans:
                # Get next pending milestone
                milestone = session.exec(
                    select(PlanMilestone)
                    .where(PlanMilestone.plan_id == plan.plan_id)
                    .where(PlanMilestone.status == "pending")
                    .order_by(PlanMilestone.order_index)
                ).first()
                
                if not milestone:
                    continue
                    
                # Get pending tasks in this milestone
                tasks = session.exec(
                    select(PlanTask)
                    .where(PlanTask.milestone_id == milestone.milestone_id)
                    .where(PlanTask.status == "pending")
                    .limit(3) # Generate content for next 3 tasks
                ).all()
                
                for task in tasks:
                    # Check if content already exists
                    existing_content = session.exec(select(ContentRepo).where(ContentRepo.task_id == task.task_id)).first()
                    if existing_content:
                        continue
                        
                    logger.info(f"Generating content for task: {task.title} (ID: {task.task_id})")
                    
                    try:
                        # Call Content Generation Agent
                        agent_task = {
                            "type": "generate_content",
                            "task_type": task.type,
                            "task_title": task.title
                        }
                        result = await agent_client.execute_task("content_generator", agent_task)
                        
                        # Save Content
                        content = ContentRepo(
                            task_id=task.task_id,
                            content_type=result.get("content_type", "text"),
                            title=result.get("title", task.title),
                            url=result.get("url"),
                            text=result.get("text"),
                            duration_sec=result.get("duration_sec"),
                            difficulty=result.get("difficulty", 0.5),
                            meta_data=result.get("metadata", {})
                        )
                        session.add(content)
                        session.commit()
                        logger.info(f"Content generated for task {task.task_id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to generate content for task {task.task_id}: {e}")

    async def send_daily_reminders(self):
        """
        Scans UserReminder table and sends notifications.
        """
        logger.info("Sending daily reminders...")
        # Implementation skipped for brevity (Mock)
        pass

learning_scheduler = LearningSchedulerService()
