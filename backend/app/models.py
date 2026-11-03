import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
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
    __table_args__ = (UniqueConstraint("account_id", "platform_game_id", name="uq_game_account_platform_id"), Index("ix_games_played_at", "played_at"))
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
    pgn: Mapped[str] = mapped_column(Text)
    import_status: Mapped[GameStatus] = mapped_column(Enum(GameStatus, name="game_status"), default=GameStatus.imported)
    analysis_status: Mapped[GameStatus] = mapped_column(Enum(GameStatus, name="analysis_status"), default=GameStatus.pending)
    account: Mapped[ConnectedAccount] = relationship(back_populates="games")
