from typing import List, Optional, Dict
from datetime import datetime
from uuid import UUID
from sqlmodel import Session, select, col
from sqlalchemy.orm import selectinload
from app.core.database import engine
from app.models.schedule import Schedule, ScheduleCreate, ScheduleUpdate, ScheduleReminder, ScheduleReminderCreate
from app.services.channel_service import channel_service
from app.models.channel import Channel
import logging

logger = logging.getLogger(__name__)

class ScheduleService:
    """
    处理日程安排（Schedule）相关业务逻辑的服务类。
    提供日程的增删改查、提醒处理、数据备份与恢复等核心功能。
    """

    async def create_schedule(self, schedule_in: ScheduleCreate) -> Schedule:
        """
        创建一个新的日程安排，并根据传入数据一并创建相关的提醒记录。

        Args:
            schedule_in (ScheduleCreate): 包含日程及其提醒信息的输入模型。

        Returns:
            Schedule: 创建成功并保存到数据库的日程记录。
        """
        with Session(engine) as session:
            # 1. 创建并保存日程主记录
            db_schedule = Schedule.model_validate(schedule_in, update={"reminders": []})
            session.add(db_schedule)
            session.commit()
            session.refresh(db_schedule)

            # 2. 如果存在提醒设置，则批量创建对应的提醒记录
            if schedule_in.reminders:
                for reminder_in in schedule_in.reminders:
                    db_reminder = ScheduleReminder(
                        schedule_id=db_schedule.id,
                        remind_at=reminder_in.remind_at,
                        type=reminder_in.type,
                        message_template=reminder_in.message_template
                    )
                    session.add(db_reminder)
                session.commit()
                # 重新刷新以加载新关联的提醒数据
                session.refresh(db_schedule)

            return db_schedule

    async def get_schedule(self, schedule_id: UUID) -> Optional[Schedule]:
        """
        根据指定的日程 ID 获取单个日程的详细信息（包含提醒列表）。

        Args:
            schedule_id (UUID): 需要查询的日程 ID。

        Returns:
            Optional[Schedule]: 查找到的日程记录，如果不存在则返回 None。
        """
        with Session(engine) as session:
            # 使用预加载 (selectinload) 避免查询提醒记录时产生 N+1 问题
            statement = select(Schedule).where(Schedule.id == schedule_id).options(selectinload(Schedule.reminders))
            return session.exec(statement).first()

    async def get_schedules(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        keyword: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Schedule]:
        """
        根据时间范围和关键字分页获取日程列表。

        Args:
            start_time (Optional[datetime], optional): 筛选的起始时间。
            end_time (Optional[datetime], optional): 筛选的结束时间。
            keyword (Optional[str], optional): 搜索关键字（匹配标题或描述）。
            limit (int, optional): 每页返回的最大记录数，默认为 100。
            offset (int, optional): 分页偏移量，默认为 0。

        Returns:
            List[Schedule]: 符合条件的日程列表（包含预加载的提醒信息）。
        """
        with Session(engine) as session:
            # 基础查询，预加载提醒记录
            query = select(Schedule).options(selectinload(Schedule.reminders))

            # 动态应用时间过滤条件
            if start_time:
                query = query.where(Schedule.start_time >= start_time)
            if end_time:
                query = query.where(Schedule.start_time <= end_time)

            # 动态应用关键字过滤条件（模糊匹配标题或描述）
            if keyword:
                search_pattern = f"%{keyword}%"
                query = query.where(col(Schedule.title).like(search_pattern) | col(Schedule.description).like(search_pattern))

            # 应用分页及排序规则
            query = query.offset(offset).limit(limit).order_by(Schedule.start_time)
            return session.exec(query).all()

    async def update_schedule(self, schedule_id: UUID, schedule_in: ScheduleUpdate) -> Optional[Schedule]:
        """
        更新指定的日程信息。如果包含提醒信息的更新，会采取先删除旧提醒再创建新提醒的策略。

        Args:
            schedule_id (UUID): 要更新的日程 ID。
            schedule_in (ScheduleUpdate): 包含更新内容的数据模型。

        Returns:
            Optional[Schedule]: 更新后的日程记录，如果该日程不存在则返回 None。
        """
        with Session(engine) as session:
            # 查找目标日程
            db_schedule = session.get(Schedule, schedule_id)
            if not db_schedule:
                return None

            update_data = schedule_in.dict(exclude_unset=True)

            # 单独处理提醒记录的更新逻辑
            if "reminders" in update_data:
                reminders_data = update_data.pop("reminders")
                # 为简化逻辑，先删除该日程下所有旧的提醒记录
                # 真实生产环境中可能需要做增量比对以保留提醒的状态 (status)
                existing_reminders = session.exec(select(ScheduleReminder).where(ScheduleReminder.schedule_id == schedule_id)).all()
                for reminder in existing_reminders:
                    session.delete(reminder)

                # 重建新的提醒记录
                if reminders_data:
                    for reminder_in in reminders_data:
                        # 兼容处理传入的是字典还是 Pydantic 模型对象
                        if isinstance(reminder_in, dict):
                            db_reminder = ScheduleReminder(
                                schedule_id=schedule_id,
                                **reminder_in
                            )
                        else:
                            db_reminder = ScheduleReminder(
                                schedule_id=schedule_id,
                                remind_at=reminder_in.remind_at,
                                type=reminder_in.type,
                                message_template=reminder_in.message_template
                            )
                        session.add(db_reminder)

            # 更新日程主表的其它字段
            for key, value in update_data.items():
                setattr(db_schedule, key, value)

            # 更新修改时间
            db_schedule.updated_at = datetime.now()
            session.add(db_schedule)
            session.commit()
            session.refresh(db_schedule)
            return db_schedule

    async def delete_schedule(self, schedule_id: UUID) -> bool:
        """
        删除指定的日程记录。由于数据库通常配置了级联删除，相关的提醒记录也会被一并删除。

        Args:
            schedule_id (UUID): 要删除的日程 ID。

        Returns:
            bool: 删除成功返回 True，如果日程不存在则返回 False。
        """
        with Session(engine) as session:
            db_schedule = session.get(Schedule, schedule_id)
            if not db_schedule:
                return False

            # 删除日程主记录，关联的 reminders 将根据外键级联策略被删除
            session.delete(db_schedule)
            session.commit()
            return True

    async def check_and_send_reminders(self):
        """
        定时任务逻辑：检查所有待发送的提醒（状态为 pending 且触发时间已到），并执行发送逻辑。

        注意：当前发送逻辑暂未完全实现（未真实调用 channel_service），
        仅为了防止死循环而将状态标记为 sent。
        """
        with Session(engine) as session:
            now = datetime.now()
            # 查找所有到达提醒时间且尚未发送的提醒记录
            reminders = session.exec(
                select(ScheduleReminder)
                .where(ScheduleReminder.status == "pending")
                .where(ScheduleReminder.remind_at <= now)
            ).all()

            for reminder in reminders:
                schedule = session.get(Schedule, reminder.schedule_id)
                if not schedule:
                    continue

                # 此处应包含查找对应频道并发送消息的真实逻辑
                # 例如：调用 channel_service 进行消息推送
                # ...

                # 暂且将状态更新为 sent，避免在下次轮询中重复处理
                reminder.status = "sent"
                session.add(reminder)
            session.commit()

    def backup_data(self) -> Dict[str, List[Dict]]:
        """
        备份系统中所有的日程和提醒数据，用于导出。

        Returns:
            Dict[str, List[Dict]]: 包含 schedules 和 reminders 列表的字典。
        """
        with Session(engine) as session:
            schedules = session.exec(select(Schedule)).all()
            reminders = session.exec(select(ScheduleReminder)).all()

            return {
                "schedules": [s.dict() for s in schedules],
                "reminders": [r.dict() for r in reminders]
            }

    def restore_data(self, data: Dict[str, List[Dict]], clear_existing: bool = False):
        """
        从备份数据中恢复日程和提醒记录。

        Args:
            data (Dict[str, List[Dict]]): 包含 schedules 和 reminders 的备份数据字典。
            clear_existing (bool, optional): 是否在导入前清空现有数据，默认为 False。
        """
        with Session(engine) as session:
            # 1. 根据配置决定是否清空旧数据
            if clear_existing:
                from sqlmodel import delete
                session.exec(delete(ScheduleReminder))
                session.exec(delete(Schedule))

            # 2. 恢复日程主数据
            for s_data in data.get("schedules", []):
                # 将字符串格式的时间转换为 datetime 对象
                for field in ["start_time", "end_time", "due_time", "created_at", "updated_at"]:
                    if s_data.get(field) and isinstance(s_data[field], str):
                        s_data[field] = datetime.fromisoformat(s_data[field])

                schedule = Schedule.model_validate(s_data)

                # 检查该 ID 的日程是否已存在
                existing = session.get(Schedule, schedule.id)
                if existing:
                    if not clear_existing:
                        # 如果存在且未指定清空，则跳过以防覆盖
                        continue
                    else:
                        # 如果指定了清空，理论上不应走到这里
                        pass
                session.add(schedule)

            # 3. 恢复提醒记录数据
            for r_data in data.get("reminders", []):
                # 将提醒时间字符串转换为 datetime 对象
                for field in ["remind_at"]:
                    if r_data.get(field) and isinstance(r_data[field], str):
                        r_data[field] = datetime.fromisoformat(r_data[field])

                reminder = ScheduleReminder.model_validate(r_data)
                session.add(reminder)

            session.commit()

schedule_service = ScheduleService()
