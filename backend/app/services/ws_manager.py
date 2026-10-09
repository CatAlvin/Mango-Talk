import asyncio
from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = defaultdict(list)
        self.user_connections: dict[int, list[WebSocket]] = defaultdict(list)
        self.guards = {}
        self.locks = {}

    async def connect(self, room_id: int, websocket: WebSocket, guard=None):
        await websocket.accept()
        self.active_connections[room_id].append(websocket)
        self.guards[websocket] = guard
        self.locks[websocket] = asyncio.Lock()

    async def connect_user(self, user_id: int, websocket: WebSocket, guard=None):
        await websocket.accept()
        self.user_connections[user_id].append(websocket)
        self.guards[websocket] = guard
        self.locks[websocket] = asyncio.Lock()

    def disconnect(self, room_id: int, websocket: WebSocket):
        self._remove(self.active_connections, room_id, websocket)

    def disconnect_user(self, user_id: int, websocket: WebSocket):
        self._remove(self.user_connections, user_id, websocket)

    def _remove(self, mapping, key, websocket):
        connections = mapping.get(key, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            mapping.pop(key, None)
        self.guards.pop(websocket, None)
        self.locks.pop(websocket, None)

    async def send_personal_message(self, websocket: WebSocket, payload: dict) -> bool:
        try:
            async with self.locks.setdefault(websocket, asyncio.Lock()):
                await asyncio.wait_for(websocket.send_json(payload), timeout=5)
            return True
        except Exception:
            return False

    async def _guarded_send(self, mapping, key, connection, payload):
        guard = self.guards.get(connection)
        if guard and not await guard():
            try:
                await connection.close(code=1008)
            except Exception:
                pass
            self._remove(mapping, key, connection)
            return
        if not await self.send_personal_message(connection, payload):
            self._remove(mapping, key, connection)

    async def broadcast(self, room_id: int, payload: dict):
        await asyncio.gather(*(self._guarded_send(self.active_connections, room_id, connection, payload) for connection in list(self.active_connections.get(room_id, []))))

    async def notify_users(self, user_ids: list[int], payload: dict):
        await asyncio.gather(*(self._guarded_send(self.user_connections, user_id, connection, payload) for user_id in user_ids for connection in list(self.user_connections.get(user_id, []))))

    def room_connection_count(self, room_id: int) -> int:
        return len(self.active_connections.get(room_id, []))


manager = ConnectionManager()
