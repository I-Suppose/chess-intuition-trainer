import enum
import uuid
from datetime import datetime
from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Platform(str, enum.Enum):
    chesscom = "chesscom"
    lichess = "lichess"


class SyncStatus(str, enum.Enum):
    pending = "PENDING"
    importing = "IMPORTING"
    imported = "IMPORTED"
    failed = "FAILED"


class GameStatus(str, enum.Enum):
    pending = "PENDING"
    importing = "IMPORTING"
    imported = "IMPORTED"
    queued = "QUEUED"
    analysing = "ANALYSING"
    analysed = "ANALYSED"
    failed = "FAILED"


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    accounts: Mapped[list["ConnectedAccount"]] = relationship(back_populates="user")


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"
    __table_args__ = (UniqueConstraint("user_id", "platform", "username", name="uq_account_owner_platform_username"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    platform: Mapped[Platform] = mapped_column(Enum(Platform, name="platform"))
    username: Mapped[str] = mapped_column(String(100))
    platform_user_id: Mapped[str | None] = mapped_column(String(100))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus, name="sync_status"), default=SyncStatus.pending)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    games: Mapped[list["Game"]] = relationship(back_populates="account")
    user: Mapped[User] = relationship(back_populates="accounts")


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (UniqueConstraint("account_id", "platform_game_id", name="uq_game_account_platform_id"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("connected_accounts.id", ondelete="CASCADE"), index=True)
    platform_game_id: Mapped[str] = mapped_column(String(255))
    game_url: Mapped[str | None] = mapped_column(Text)
    white_player: Mapped[str | None] = mapped_column(String(100))
    black_player: Mapped[str | None] = mapped_column(String(100))
    user_colour: Mapped[str | None] = mapped_column(String(5))
    opponent_username: Mapped[str | None] = mapped_column(String(100))
    result: Mapped[str | None] = mapped_column(String(20))
    played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    time_control: Mapped[str | None] = mapped_column(String(100))
    opening_name: Mapped[str | None] = mapped_column(String(255))
    opening_line: Mapped[str | None] = mapped_column(Text)
    pgn: Mapped[str] = mapped_column(Text)
    import_status: Mapped[GameStatus] = mapped_column(Enum(GameStatus, name="game_status"), default=GameStatus.imported)
    analysis_status: Mapped[GameStatus] = mapped_column(Enum(GameStatus, name="analysis_status"), default=GameStatus.pending)
    account: Mapped[ConnectedAccount] = relationship(back_populates="games")


class GameAnalysis(Base):
    __tablename__ = "game_analysis"
    __table_args__ = (UniqueConstraint("game_id", "ply", name="uq_analysis_game_ply"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    move_number: Mapped[int] = mapped_column(Integer)
    ply: Mapped[int] = mapped_column(Integer)
    fen: Mapped[str] = mapped_column(Text)
    side_to_move: Mapped[str] = mapped_column(String(5))
    played_move_uci: Mapped[str] = mapped_column(String(8))
    best_move_uci: Mapped[str] = mapped_column(String(8))
    alternative_moves: Mapped[list] = mapped_column(JSON, default=list)
    evaluation_before: Mapped[dict] = mapped_column(JSON)
    evaluation_after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    principal_variation: Mapped[list] = mapped_column(JSON, default=list)
    engine_depth: Mapped[int] = mapped_column(Integer)
    move_classification: Mapped[str] = mapped_column(String(32), default="UNCLASSIFIED")
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    classification_reason: Mapped[str] = mapped_column(Text, default="")
    material_sacrifice: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Puzzle(Base):
    __tablename__ = "puzzles"
    __table_args__ = (UniqueConstraint("user_id", "position_fingerprint", name="uq_puzzle_user_position"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("game_analysis.id", ondelete="CASCADE"), index=True)
    position_fingerprint: Mapped[str] = mapped_column(String(64))
    fen: Mapped[str] = mapped_column(Text)
    side_to_move: Mapped[str] = mapped_column(String(5))
    puzzle_category: Mapped[str] = mapped_column(String(40), index=True)
    priority: Mapped[int] = mapped_column(Integer, index=True)
    solution_uci: Mapped[str] = mapped_column(String(8))
    accepted_solutions: Mapped[list] = mapped_column(JSON, default=list)
    principal_variation: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text)
    game_move_number: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PuzzleAttempt(Base):
    __tablename__ = "puzzle_attempts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    puzzle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("puzzles.id", ondelete="CASCADE"), index=True)
    submitted_move: Mapped[str] = mapped_column(String(8))
    is_correct: Mapped[bool] = mapped_column(Boolean)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    time_taken: Mapped[float | None] = mapped_column(Float)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
