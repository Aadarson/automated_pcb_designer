import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()
AsyncSessionLocal = None
engine = None

class Database:
    def __init__(self):
        self.engine = None
        self._session_factory = None

    async def connect(self):
        global engine, AsyncSessionLocal
        db_url = settings.DATABASE_URL
        
        try:
            logger.info(f"Attempting connection to primary DB: {db_url}")
            engine = create_async_engine(db_url, echo=False, connect_args={"timeout": 5})
            async with engine.begin() as conn:
                from backend.models.database import Project, DesignVersion
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Successfully connected to PostgreSQL.")
        except Exception as e:
            fallback_url = "sqlite+aiosqlite:///./pcb_automation.db"
            logger.warning(f"Primary DB failed ({e}). Falling back to local SQLite: {fallback_url}")
            engine = create_async_engine(fallback_url, echo=False)
            async with engine.begin() as conn:
                from backend.models.database import Project, DesignVersion
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Successfully connected to SQLite fallback.")

        AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        self.engine = engine
        self._session_factory = AsyncSessionLocal

    async def disconnect(self):
        if self.engine:
            await self.engine.dispose()

db = Database()
