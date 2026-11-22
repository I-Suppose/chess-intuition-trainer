"""Run schema migrations for Vercel production deployments."""

import os
import subprocess
import sys


def main() -> None:
    # Preview builds may not have the production database secret and must not
    # mutate the production schema.
    if os.getenv("VERCEL_ENV") != "production":
        print("Skipping database migrations outside the Vercel production environment.")
        return
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL must be configured for the Vercel backend service.")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


if __name__ == "__main__":
    main()
