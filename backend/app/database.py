from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=1,
    max_overflow=0,
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
