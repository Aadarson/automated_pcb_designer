class MockDatabase:
    def __init__(self):
        self.pool = None

    async def connect(self):
        pass

    async def disconnect(self):
        pass

db = MockDatabase()
