"""Persist the account-combining preference."""
import sqlalchemy as sa
from alembic import op

revision = "0005_combine_accounts"
down_revision = "0004_puzzle_reveals"
branch_labels = None
depends_on = None


def upgrade():
    # Existing users did not have an account-combining preference. Keep their
    # most recently connected live profile so the default is a single source.
    op.execute("""
        DELETE FROM connected_accounts
        WHERE id NOT IN (
            SELECT DISTINCT ON (user_id) id
            FROM connected_accounts
            WHERE is_connected = TRUE
            ORDER BY user_id, connected_at DESC
        )
    """)
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "combine_accounts" not in columns:
        op.add_column("users", sa.Column("combine_accounts", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("users", "combine_accounts")
