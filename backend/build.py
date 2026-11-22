"""Run schema migrations for Vercel production deployments."""

import hashlib
import os
import platform
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path


STOCKFISH_URL = (
    "https://github.com/official-stockfish/Stockfish/releases/download/sf_19/"
    "stockfish-linux-x86-64-universal.tar.gz"
)
STOCKFISH_SHA256 = "9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f"


def install_vercel_stockfish() -> None:
    """Bundle the pinned official Linux engine for Vercel analysis workers."""
    if not (os.getenv("VERCEL") or os.getenv("VERCEL_ENV")):
        return
    if sys.platform != "linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        print("Skipping bundled Stockfish; this is not a Vercel Linux x86-64 build.")
        return

    install_dir = Path(__file__).resolve().parent / "bin"
    engine_path = install_dir / "stockfish"
    if engine_path.is_file():
        return

    install_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="stockfish-", suffix=".tar.gz") as archive:
        print("Downloading pinned Stockfish 19 for Vercel analysis workers...")
        request = urllib.request.Request(STOCKFISH_URL, headers={"User-Agent": "ChessIntuitionTrainer"})
        with urllib.request.urlopen(request, timeout=120) as response, open(archive.name, "wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)

        digest = hashlib.sha256(Path(archive.name).read_bytes()).hexdigest()
        if digest != STOCKFISH_SHA256:
            raise RuntimeError("Downloaded Stockfish archive failed SHA-256 verification.")

        with tarfile.open(archive.name, mode="r:gz") as bundle:
            engine_member = next(
                (member for member in bundle.getmembers()
                 if member.isfile() and member.name.endswith("/stockfish-linux-x86-64-universal")),
                None,
            )
            license_member = next(
                (member for member in bundle.getmembers()
                 if member.isfile() and member.name.endswith("/Copying.txt")),
                None,
            )
            if engine_member is None or license_member is None:
                raise RuntimeError("The Stockfish archive is missing its engine or license file.")

            engine_stream = bundle.extractfile(engine_member)
            license_stream = bundle.extractfile(license_member)
            if engine_stream is None or license_stream is None:
                raise RuntimeError("Could not read the Stockfish engine or license from its archive.")
            with engine_stream, open(engine_path, "wb") as output:
                while chunk := engine_stream.read(1024 * 1024):
                    output.write(chunk)
            with license_stream, open(install_dir / "Stockfish-Copying.txt", "wb") as output:
                while chunk := license_stream.read(1024 * 1024):
                    output.write(chunk)

    engine_path.chmod(0o755)
    print(f"Bundled Stockfish at {engine_path}.")


def main() -> None:
    install_vercel_stockfish()
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
