"""Persist the account-combining preference."""
import sqlalchemy as sa
from alembic import op

revision = "0005_combine_accounts"
down_revision = "0004_puzzle_reveals"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # This migration only adds the preference. Preserve all connected accounts
    # and their imported games while upgrading existing installations.
    user_columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "combine_accounts" not in user_columns:
        op.add_column("users", sa.Column("combine_accounts", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("users", "combine_accounts")
