import asyncio
import json
from typing import List
from fastapi import WebSocket
import psutil
import logging

logger = logging.getLogger("xedy.websocket")

class ConnectionManager:
    """
    Manages active WebSocket connections to broadcast data to the frontend dashboard.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket Client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket Client disconnected. Active: {len(self.active_connections)}")

    async def broadcast_tick(self, symbol: str, bid: float, ask: float, time_sec: int):
        """Broadcast real-time market data."""
        if not self.active_connections:
            return
            
        payload = {
            "type": "tick",
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "time": time_sec
        }
        await self._broadcast_json(payload)

    async def broadcast_status(self, broker_status: str, mt5_status: str, ai_status: str):
        """Broadcast system status."""
        
        # Read system metrics
        cpu_usage = psutil.cpu_percent(interval=None)
        ram_info = psutil.virtual_memory()
        ram_used_gb = ram_info.used / (1024**3)
        
        swap = psutil.swap_memory()
        virtual_ram_total_gb = swap.total / (1024**3)
        virtual_ram_used_gb = swap.used / (1024**3)
        
        combined_total = ram_info.total + swap.total
        combined_used = ram_info.used + swap.used
        combined_percent = (combined_used / combined_total) * 100 if combined_total > 0 else 0
        
        payload = {
            "type": "system_status",
            "broker": broker_status,
            "mt5": mt5_status,
            "ai": ai_status,
            "cpu": f"{cpu_usage:.1f}%",
            "ram": f"{ram_used_gb:.1f}GB",
            "ram_percent": ram_info.percent,
            "vram_total": f"{virtual_ram_total_gb:.1f}GB",
            "vram_used": f"{virtual_ram_used_gb:.1f}GB",
            "vram_percent": swap.percent,
            "combined_total": f"{combined_total / (1024**3):.1f}GB",
            "combined_used": f"{combined_used / (1024**3):.1f}GB",
            "combined_percent": combined_percent
        }
        await self._broadcast_json(payload)

    async def broadcast_signal(self, confidence: float, signal: str):
        """Broadcast AI state."""
        if not self.active_connections:
            return
            
        payload = {
            "type": "ai_signal",
            "confidence": confidence,
            "signal": signal
        }
        await self._broadcast_json(payload)

    async def _broadcast_json(self, data: dict):
        # We must gather all sends to avoid blocking
        text_data = json.dumps(data)
        tasks = []
        for connection in self.active_connections:
            # We don't await each directly to prevent one slow client from delaying others
            tasks.append(asyncio.create_task(self._send_safe(connection, text_data)))
            
        if tasks:
            await asyncio.gather(*tasks)

    async def _send_safe(self, websocket: WebSocket, text_data: str):
        try:
            await websocket.send_text(text_data)
        except Exception:
            self.disconnect(websocket)

# Global singleton for the app to use
ws_manager = ConnectionManager()
