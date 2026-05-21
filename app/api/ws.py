"""WebSocket handler for real-time progress streaming."""

import json
import asyncio
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections per task."""

    def __init__(self):
        # task_id -> set of WebSocket connections
        self._connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, task_id: int, ws: WebSocket):
        await ws.accept()
        if task_id not in self._connections:
            self._connections[task_id] = set()
        self._connections[task_id].add(ws)

    def disconnect(self, task_id: int, ws: WebSocket):
        if task_id in self._connections:
            self._connections[task_id].discard(ws)
            if not self._connections[task_id]:
                del self._connections[task_id]

    async def broadcast(self, task_id: int, message: dict):
        """Send message to all connections watching a task."""
        if task_id not in self._connections:
            return
        dead = set()
        for ws in self._connections[task_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._connections[task_id].discard(ws)
        if not self._connections.get(task_id):
            self._connections.pop(task_id, None)

    async def broadcast_log(self, task_id: int, level: str, message: str):
        """Convenience: broadcast a log message."""
        await self.broadcast(task_id, {
            "type": "log",
            "level": level,
            "message": message,
        })

    async def broadcast_progress(
        self, task_id: int, phase: str, current: int = 0, total: int = 0, **extra
    ):
        """Convenience: broadcast progress update."""
        payload = {
            "type": "progress",
            "phase": phase,
            "current": current,
            "total": total,
            **extra,
        }
        await self.broadcast(task_id, payload)


# Global connection manager instance
ws_manager = ConnectionManager()


@router.websocket("/ws/tasks/{task_id}/logs")
async def task_log_ws(websocket: WebSocket, task_id: int):
    await ws_manager.connect(task_id, websocket)
    try:
        # Keep connection alive, receive pings
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(task_id, websocket)
    except Exception:
        ws_manager.disconnect(task_id, websocket)
