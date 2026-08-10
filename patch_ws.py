import re

file_path = "backend/api/websocket.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

v39_broadcast = """
    async def broadcast_v39_causal(self, v39_payload: dict):
        \"\"\"Broadcast V39 Causal Engine 17-step data\"\"\"
        if not self.active_connections:
            return
            
        payload = {
            "type": "v39_data",
            "data": v39_payload
        }
        await self._broadcast_json(payload)
"""

if "def broadcast_v39_causal" not in content:
    content = content.replace("    async def _broadcast_json", v39_broadcast + "\n    async def _broadcast_json")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Added broadcast_v39_causal to websocket.py")
else:
    print("broadcast_v39_causal already exists.")
