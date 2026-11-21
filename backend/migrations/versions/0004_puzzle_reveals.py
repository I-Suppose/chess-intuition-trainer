"""Track puzzles finished by revealing the solution."""
import sqlalchemy as sa
from alembic import op

revision = "0004_puzzle_reveals"
down_revision = "0003_multimove_puzzle_analysis"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"]: column for column in sa.inspect(bind).get_columns("puzzle_attempts")}
    if "revealed" not in columns:
        op.add_column("puzzle_attempts", sa.Column("revealed", sa.Boolean(), nullable=False, server_default=sa.false()))
    if not columns["submitted_move"]["nullable"]:
        op.alter_column("puzzle_attempts", "submitted_move", existing_type=sa.String(length=8), nullable=True)


def downgrade():
    op.execute("UPDATE puzzle_attempts SET submitted_move = '0000' WHERE submitted_move IS NULL")
    op.alter_column("puzzle_attempts", "submitted_move", existing_type=sa.String(length=8), nullable=False)
    op.drop_column("puzzle_attempts", "revealed")
