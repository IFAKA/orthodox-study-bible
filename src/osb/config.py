"""Application configuration and paths."""

import os
from pathlib import Path

from dotenv import load_dotenv
from platformdirs import user_data_dir

# Load a .env file (searched from the cwd upward) before reading env vars, so
# OLLAMA_* settings can live in a project-local .env instead of the shell.
load_dotenv()

APP_NAME = "osb"
APP_DIR = Path(user_data_dir(APP_NAME))
DB_PATH = APP_DIR / "osb.db"
LOG_PATH = APP_DIR / "osb.log"

EPUB_HASH_KEY = "epub_sha256"
IMPORT_DATE_KEY = "import_date"
SCHEMA_VERSION_KEY = "schema_version"
LAST_SESSION_DATE_KEY = "last_session_date"

# Ollama — local by default; point at Ollama Cloud (https://ollama.com) by
# setting OLLAMA_BASE_URL and OLLAMA_API_KEY. The model can also be overridden,
# e.g. a cloud model like "gpt-oss:120b".
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")
MAX_CONTEXT_TOKENS = 3000


def ollama_headers() -> dict[str, str]:
    """Auth headers for Ollama requests; empty for a local instance."""
    if OLLAMA_API_KEY:
        return {"Authorization": f"Bearer {OLLAMA_API_KEY}"}
    return {}


def ollama_is_local() -> bool:
    """True when targeting a local Ollama daemon rather than a remote/cloud host."""
    return "localhost" in OLLAMA_BASE_URL or "127.0.0.1" in OLLAMA_BASE_URL

JURISDICTION = "OCA"

# Pre-built DB download (GitHub Releases)
# Update DB_RELEASE_SHA256 after running: uv run python scripts/build_release_db.py
DB_RELEASE_URL = "https://github.com/IFAKA/orthodox-study-bible/releases/download/db-v1/osb.db.gz"
DB_RELEASE_SHA256 = "cfca96f6291da23f868a7929abb9f4bfa259b62db91ca91085636d7e7c854f11"

# Minimum sidebar width in columns
MIN_SIDEBAR_WIDTH = 18
