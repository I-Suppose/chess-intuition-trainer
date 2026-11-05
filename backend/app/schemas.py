import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models import Platform, SyncStatus, GameStatus


class AccountConnect(BaseModel):
    platform: Platform
    username: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("username")
    @classmethod
    def trim_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username cannot be empty.")
        return value


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    platform: Platform
    username: str
    last_synced_at: datetime | None
    sync_status: SyncStatus
    game_count: int = 0


class GameOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    account_id: uuid.UUID
    platform_game_id: str
    game_url: str | None
    white_player: str | None
    black_player: str | None
    user_colour: str | None
    opponent_username: str | None
    result: str | None
    played_at: datetime | None
    time_control: str | None
    opening_name: str | None
    opening_line: str | None
    import_status: GameStatus
    analysis_status: GameStatus


class PuzzleAttemptIn(BaseModel):
    move_uci: str = Field(min_length=4, max_length=5, pattern=r"^[a-h][1-8][a-h][1-8][qrbn]?$")
    line_step: int = Field(default=0, ge=0, le=80)
    time_taken: float | None = Field(default=None, ge=0, le=86400)


class PuzzleAttemptOut(BaseModel):
    attempt_id: uuid.UUID
    is_correct: bool
    message: str
    feedback: str
    line_complete: bool
    opponent_move_uci: str | None


class PuzzleSolutionOut(BaseModel):
    solution_move_uci: str
    solution_move_san: str
    principal_variation_uci: list[str]
    principal_variation_san: list[str]
    explanation: str
    played_move_san: str | None
    move_explanations: list[dict]
