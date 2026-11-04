"""Add opening lines, engine analysis, generated puzzles, and attempts."""
import sqlalchemy as sa
from alembic import op
from app.database import Base
from app import models  # noqa: F401

revision = "0002_analysis_openings"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("games")}
    if "opening_line" not in columns:
        op.add_column("games", sa.Column("opening_line", sa.Text(), nullable=True))
    Base.metadata.create_all(bind=bind)


def downgrade():
    op.drop_table("puzzle_attempts")
    op.drop_table("puzzles")
    op.drop_table("game_analysis")
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("games")}
    if "opening_line" in columns:
        op.drop_column("games", "opening_line")
