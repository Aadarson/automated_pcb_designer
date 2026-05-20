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
        self.latest_status = {}

    def _get_queue(self, channel: str):
        if channel not in self.channels:
            self.channels[channel] = asyncio.Queue()
        return self.channels[channel]

    async def publish_event(self, job_id: str, event_data: dict):
        channel = f"job:{job_id}:events"
        await self.publish(channel, json.dumps(event_data))

    async def publish(self, channel: str, message: str):
        if "events" in channel:
             job_id = channel.split(":")[1]
             try:
                 self.latest_status[job_id] = json.loads(message)
             except: pass
        q = self._get_queue(channel)
        await q.put(message)

    async def get_subscriber(self, channel: str = None):
        if channel:
            q = self._get_queue(channel)
        else:
            q = asyncio.Queue() # Temp fallback
        return MockPubSub(q)

redis_client = InMemoryRedisClient()
