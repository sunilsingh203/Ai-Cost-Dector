import asyncio

from fastapi import WebSocket


class ProgressManager:
    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = {}
        self._buffers: dict[int, list[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, analysis_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(analysis_id, []).append(websocket)
            pending = self._buffers.pop(analysis_id, [])

        for message in pending:
            await websocket.send_json({"message": message})

    async def disconnect(self, analysis_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(analysis_id, [])
            if websocket in connections:
                connections.remove(websocket)
            if not connections:
                self._connections.pop(analysis_id, None)

    async def send_progress(self, analysis_id: int, message: str) -> None:
        payload = {"message": message}
        async with self._lock:
            connections = list(self._connections.get(analysis_id, []))
            if not connections:
                self._buffers.setdefault(analysis_id, []).append(message)
                return

        dead: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                dead.append(websocket)

        if dead:
            async with self._lock:
                live = self._connections.get(analysis_id, [])
                self._connections[analysis_id] = [
                    ws for ws in live if ws not in dead
                ]
