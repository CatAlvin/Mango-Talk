import asyncio
import json
import sys
import websockets
from ws_helpers import safe_event

if len(sys.argv) != 3:
    print("Usage: python ws_listen.py <room_id> <token>")
    sys.exit(1)

room_id = sys.argv[1]
token = sys.argv[2]

url = f"ws://127.0.0.1:8000/ws/rooms/{room_id}?token={token}"

async def main():
    async with websockets.connect(url) as ws:
        print(f"Connected to room {room_id}")
        async def heartbeat():
            while True:
                await asyncio.sleep(20)
                await ws.send(json.dumps({"action": "ping"}))
        task = asyncio.create_task(heartbeat())
        try:
            while True:
                print(safe_event(await ws.recv()))
        finally:
            task.cancel()

asyncio.run(main())
