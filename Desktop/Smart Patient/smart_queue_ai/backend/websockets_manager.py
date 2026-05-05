from fastapi import WebSocket
from typing import List, Dict

class ConnectionManager:
    def __init__(self):
        # Maps doctor_id to a list of active websocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, doctor_id: int):
        await websocket.accept()
        if doctor_id not in self.active_connections:
            self.active_connections[doctor_id] = []
        self.active_connections[doctor_id].append(websocket)

    def disconnect(self, websocket: WebSocket, doctor_id: int):
        if doctor_id in self.active_connections:
            if websocket in self.active_connections[doctor_id]:
                self.active_connections[doctor_id].remove(websocket)

    async def broadcast_queue_update(self, doctor_id: int):
        """
        Sends a ping to all clients watching this doctor's queue.
        The clients will then refetch the queue data via HTTP, or 
        we could send the full queue data directly. For simplicity and 
        data consistency, we tell them to "refresh".
        """
        if doctor_id in self.active_connections:
            for connection in self.active_connections[doctor_id]:
                try:
                    await connection.send_json({"type": "queue_update"})
                except Exception as e:
                    # Connection might be closed
                    pass

manager = ConnectionManager()
