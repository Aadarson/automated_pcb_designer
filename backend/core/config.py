from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/pcbdb"
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "change-this-to-a-secure-random-string"
    KICAD_FOOTPRINT_LIB_PATH: str = "./libs/kicad-footprints"
    STORAGE_PATH: str = "./storage/designs"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24h

    class Config:
        env_file = ".env"

settings = Settings()
