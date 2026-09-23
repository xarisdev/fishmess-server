from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
ENV_PATH = CURRENT_DIR.parent.parent / ".env"

class Application(BaseSettings):
    APP_NAME: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8"
    )

class DataBase(BaseSettings):
    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8"
    )

class Settings(
    Application,
    DataBase
):
    pass

settings = Settings()