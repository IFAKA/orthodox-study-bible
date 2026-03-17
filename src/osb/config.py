"""Application configuration and paths."""

from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "osb"
APP_DIR = Path(user_data_dir(APP_NAME))
DB_PATH = APP_DIR / "osb.db"
LOG_PATH = APP_DIR / "osb.log"

EPUB_HASH_KEY = "epub_sha256"
IMPORT_DATE_KEY = "import_date"
SCHEMA_VERSION_KEY = "schema_version"
LAST_SESSION_DATE_KEY = "last_session_date"

OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_BASE_URL = "http://localhost:11434"
MAX_CONTEXT_TOKENS = 3000

JURISDICTION = "OCA"

# Pre-built DB download (GitHub Releases)
# Update DB_RELEASE_SHA256 after running: uv run python scripts/build_release_db.py
DB_RELEASE_URL = "https://github.com/IFAKA/orthodox-study-bible/releases/download/db-v1/osb.db.gz"
DB_RELEASE_SHA256 = "cfca96f6291da23f868a7929abb9f4bfa259b62db91ca91085636d7e7c854f11"

# Minimum sidebar width in columns
MIN_SIDEBAR_WIDTH = 18
