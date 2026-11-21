"""Add application-managed password authentication."""
import sqlalchemy as sa
from alembic import op

revision = "0006_local_password_auth"
down_revision = "0005_combine_accounts"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "password_hash" not in columns:
        op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    constraints = {item.get("name") for item in sa.inspect(bind).get_unique_constraints("users")}
    if "uq_users_email" not in constraints:
        op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade():
    bind = op.get_bind()
    constraints = {item.get("name") for item in sa.inspect(bind).get_unique_constraints("users")}
    if "uq_users_email" in constraints:
        op.drop_constraint("uq_users_email", "users", type_="unique")
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "password_hash" in columns:
        op.drop_column("users", "password_hash")
