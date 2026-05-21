"""Task scheduler — runs periodic monitoring jobs using APScheduler."""

import datetime
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from sqlalchemy import select

from app.models.database import async_session
from app.models.task import MonitorTask
from app.services.task_runner import ScrapingTaskRunner


class TaskScheduler:
    """Manages periodic scraping tasks.

    On app startup, loads all enabled tasks from DB and schedules them.
    When a task is created/updated, the schedule is adjusted.
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(jobstores={"default": MemoryJobStore()})
        self._job_map = {}  # task_id -> job_id

    def start(self):
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown(wait=False)

    async def load_tasks_from_db(self):
        """Load all enabled tasks and schedule them."""
        async with async_session() as db:
            result = await db.execute(
                select(MonitorTask).where(MonitorTask.enabled == True)
            )
            tasks = result.scalars().all()

        for task in tasks:
            self.schedule_task(task.id, task.interval_minutes)

    def schedule_task(self, task_id: int, interval_minutes: int):
        """Add or update a scheduled job for a task."""
        # Remove existing job if any
        self.unschedule_task(task_id)

        job_id = f"task_{task_id}"
        self._job_map[task_id] = job_id

        self.scheduler.add_job(
            self._run_task_wrapper,
            trigger="interval",
            minutes=interval_minutes,
            id=job_id,
            args=[task_id],
            replace_existing=True,
            # Add jitter to avoid all tasks firing at the same time
            jitter=30,
        )

    def unschedule_task(self, task_id: int):
        """Remove a scheduled job."""
        job_id = self._job_map.pop(task_id, None)
        if job_id and self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

    async def _run_task_wrapper(self, task_id: int):
        """Wrapper that runs the task and handles errors."""
        runner = ScrapingTaskRunner()
        try:
            await runner.run(task_id)
        except Exception as e:
            print(f"[Scheduler] Task {task_id} failed: {e}")
