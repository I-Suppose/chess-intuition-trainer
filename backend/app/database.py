from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    # Vercel can serve several API requests while an import worker is also
    # active in a warm instance. Leave enough connections for that overlap.
    pool_size=3,
    max_overflow=2,
    pool_timeout=15,
    pool_recycle=1800,
    # Supabase's transaction pooler does not retain prepared statements
    # between transactions. Disabling psycopg auto-prepare is compatible with
    # both pooled and direct Postgres connections.
    connect_args={"prepare_threshold": 0},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
