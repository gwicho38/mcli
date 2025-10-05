"""WebSocket API routes for real-time updates"""

import asyncio
import json
from typing import Dict, Set

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from mcli.ml.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            if not self.active_connections[channel]:
                del self.active_connections[channel]

    async def broadcast(self, channel: str, message: dict):
        if channel in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.add(connection)

            # Remove disconnected clients
            for conn in disconnected:
                self.disconnect(conn, channel)


manager = ConnectionManager()


@router.websocket("/predictions")
async def websocket_predictions(websocket: WebSocket):
    """Real-time prediction updates"""
    await manager.connect(websocket, "predictions")
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, "predictions")


@router.websocket("/prices")
async def websocket_prices(websocket: WebSocket):
    """Real-time price updates"""
    await manager.connect(websocket, "prices")
    try:
        while True:
            await asyncio.sleep(1)
            # Send mock price update
            await websocket.send_json(
                {
                    "type": "price_update",
                    "ticker": "AAPL",
                    "price": 150.00 + (asyncio.get_event_loop().time() % 10),
                }
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket, "prices")
