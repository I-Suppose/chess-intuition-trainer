"""Track full puzzle completion after multi move lines."""
import sqlalchemy as sa
from alembic import op

revision = "0003_multimove_puzzle_analysis"
down_revision = "0002_analysis_openings"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("puzzle_attempts")}
    if "completed" not in columns:
        op.add_column("puzzle_attempts", sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE puzzle_attempts SET completed = TRUE WHERE is_correct = TRUE")


def downgrade():
    op.drop_column("puzzle_attempts", "completed")
