"""Background task runner — ties orchestrator to WebSocket progress reporting."""

import datetime
import asyncio
from sqlalchemy import select

from app.models.database import async_session
from app.models.task import MonitorTask
from app.api.ws import ws_manager
from app.services.orchestrator import XHSOrchestrator
from app.adapters.cdp_manager import CDPManager
from app.adapters.mediacrawler import MediaCrawlerAdapter
from app.analysis.scorer import CommentAnalyzer

# Track running tasks so they can be stopped
_running_tasks: dict[int, asyncio.Task] = {}


class ScrapingTaskRunner:
    """Runs a single scraping cycle, reporting progress via WebSocket."""

    def __init__(self):
        self.cdp_manager = CDPManager()
        self.crawler = MediaCrawlerAdapter()
        self.analyzer = CommentAnalyzer()

    async def run(self, task_id: int):
        """Execute one scrape-and-analyze cycle for a task."""
        async def progress_wrapper(msg, level="info"):
            await ws_manager.broadcast_log(task_id, level, msg)

        orchestrator = XHSOrchestrator(
            cdp_manager=self.cdp_manager,
            crawler=self.crawler,
            analyzer=self.analyzer,
            progress_callback=progress_wrapper,
        )

        # Get task from DB and update status
        async with async_session() as db:
            result = await db.execute(
                select(MonitorTask).where(MonitorTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                await ws_manager.broadcast_log(
                    task_id, "error", f"Task {task_id} not found"
                )
                return

            task.status = "running"
            task.last_run_at = datetime.datetime.utcnow()
            await db.commit()

        try:
            # Check for cancellation before each major step
            async def check_cancel():
                if _running_tasks.get(task_id, None) and _running_tasks[task_id].cancelled():
                    raise asyncio.CancelledError()

            await check_cancel()
            analysis = await orchestrator.run_task(task)

            await check_cancel()

            async with async_session() as db:
                result = await db.execute(
                    select(MonitorTask).where(MonitorTask.id == task_id)
                )
                task = result.scalar_one_or_none()
                if task:
                    task.status = "idle"
                    await db.commit()

            await ws_manager.broadcast(task_id, {
                "type": "complete",
                "data": {
                    "posts_scraped": analysis.posts_scraped,
                    "comments_scraped": analysis.comments_scraped,
                    "useful_comments_found": analysis.useful_comments_found,
                    "status": analysis.status,
                },
            })

        except asyncio.CancelledError:
            # Task was stopped by user
            async with async_session() as db:
                result = await db.execute(
                    select(MonitorTask).where(MonitorTask.id == task_id)
                )
                task = result.scalar_one_or_none()
                if task:
                    task.status = "idle"
                    await db.commit()
            await ws_manager.broadcast_log(task_id, "warn", "Task stopped by user")
            await ws_manager.broadcast(task_id, {
                "type": "complete",
                "data": {"status": "stopped", "message": "Task stopped by user"},
            })

        except Exception as e:
            async with async_session() as db:
                result = await db.execute(
                    select(MonitorTask).where(MonitorTask.id == task_id)
                )
                task = result.scalar_one_or_none()
                if task:
                    task.status = "error"
                    await db.commit()

            await ws_manager.broadcast(task_id, {
                "type": "error",
                "message": str(e),
            })
        finally:
            # Clean up the orchestrator's browser connection
            try:
                await self.cdp_manager.disconnect()
            except Exception:
                pass
            _running_tasks.pop(task_id, None)


def start_task(task_id: int) -> bool:
    """Start a task in the background. Returns False if already running."""
    if task_id in _running_tasks and not _running_tasks[task_id].done():
        return False

    runner = ScrapingTaskRunner()
    task = asyncio.create_task(runner.run(task_id))
    _running_tasks[task_id] = task
    return True


async def stop_task(task_id: int) -> bool:
    """Stop a running task. Returns False if not running."""
    task = _running_tasks.get(task_id)
    if task and not task.done():
        task.cancel()
        return True
    return False


def is_task_running(task_id: int) -> bool:
    """Check if a task is currently running."""
    task = _running_tasks.get(task_id)
    return task is not None and not task.done()
