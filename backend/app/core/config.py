from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://chess:chess@localhost:5432/chess_trainer"
    redis_url: str = "redis://localhost:6379/0"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    initial_game_import_limit: int = 100
    stockfish_path: str = ""
    stockfish_threads: int = 2
    stockfish_hash_mb: int = 256
    stockfish_multipv: int = 3
    stockfish_depth: int = 16
    stockfish_time_limit: float = 2.0
    cors_origins: str = "http://localhost:3000"


settings = Settings()
