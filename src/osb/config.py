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

OLLAMA_MODEL = "llama3.2"
OLLAMA_BASE_URL = "http://localhost:11434"
MAX_CONTEXT_TOKENS = 3000

JURISDICTION = "OCA"

# Minimum sidebar width in columns
MIN_SIDEBAR_WIDTH = 18
