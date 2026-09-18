import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://127.0.0.1:8000/api/v1/ws') as ws:
        await ws.send(json.dumps({'action': 'update_qwen_settings', 'autotrade': True, 'min_confidence': 50, 'risk_model': 'Conservative'}))
        print('Sent update_qwen_settings')
        for _ in range(5):
            res = await ws.recv()
            data = json.loads(res)
            if data.get('type') == 'v39_data':
                print('v39_data conditions:', data['data']['conditions'])

asyncio.run(test())
