from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[3] / ".env", extra="ignore")
    database_url: str = "mysql+pymysql://root:change-me@127.0.0.1:3306/chess_trainer?charset=utf8mb4"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = ""
    jwt_expiry_days: int = 7
    initial_game_import_limit: int = 100
    stockfish_path: str = ""
    stockfish_threads: int = 2
    stockfish_hash_mb: int = 256
    stockfish_multipv: int = 3
    stockfish_depth: int = 16
    stockfish_time_limit: float = 2.0
    stockfish_game_time_limit: float = 0.75
    stockfish_scan_depth: int = 9
    stockfish_scan_time_limit: float = 0.1
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_mysql_url(cls, value: str) -> str:
        if isinstance(value, str):
            if value.startswith("mysql://"):
                return value.replace("mysql://", "mysql+pymysql://", 1)
            if value.startswith("mariadb://"):
                return value.replace("mariadb://", "mysql+pymysql://", 1)
        return value

settings = Settings()
