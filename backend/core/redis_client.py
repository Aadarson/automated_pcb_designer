import asyncio
import json

class MockPubSub:
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue

    async def subscribe(self, channel: str):
        pass

    async def unsubscribe(self, channel: str):
        pass

    async def listen(self):
        while True:
            data = await self.queue.get()
            yield {'type': 'message', 'data': data}

class InMemoryRedisClient:
    def __init__(self):
        self.channels = {}

    def _get_queue(self, channel: str):
        if channel not in self.channels:
            self.channels[channel] = asyncio.Queue()
        return self.channels[channel]

    async def publish_event(self, job_id: str, event_data: dict):
        channel = f"job:{job_id}:events"
        q = self._get_queue(channel)
        await q.put(json.dumps(event_data))

    async def get_subscriber(self, channel: str = None):
        if channel:
            q = self._get_queue(channel)
        else:
            q = asyncio.Queue() # Temp fallback
        return MockPubSub(q)

redis_client = InMemoryRedisClient()
