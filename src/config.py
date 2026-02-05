from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent

class Settings(BaseSettings):

    # Настройки приложения
    APP_HOST: str
    APP_PORT: int
    DEBUG: bool

    # Бд
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    # Редис как кеш
    REDIS_HOST: str = '127.0.0.1'
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str
    REDIS_DB_CACHE: int = 1

    # Логирование
    LOG_LEVEL: str = 'DEBUG'

    model_config = SettingsConfigDict(env_file=BASE_DIR/".env",
                                      extra="ignore")

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def DATABASE_URL_ALEMBIC(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://:{self.REDIS_USER_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}"


settings = Settings()
