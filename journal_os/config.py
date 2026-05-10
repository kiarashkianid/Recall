"""
config.py
─────────
Single source of truth for every constant in Journal OS.
Edit DB credentials, API key, and theme values here.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
ENV_PATH = ROOT_DIR / ".env"


def _load_dotenv(path: Path = ENV_PATH) -> None:
    """Load simple KEY=VALUE pairs from .env without overriding shell env."""
    if not path.exists():
        return

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

# ──────────────────────────────────────────────
#  API
# ──────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_LLM_MODEL       = "gpt-4o"

# ──────────────────────────────────────────────
#  DATABASE  (PostgreSQL — structured storage)
# ──────────────────────────────────────────────
DB_CONFIG: dict = {
    "dbname":   os.getenv("POSTGRES_DB", "journal_db"),
    "user":     os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "1382"),
    "host":     os.getenv("POSTGRES_HOST", "localhost"),
    "port":     os.getenv("POSTGRES_PORT", "5432"),
}

# ──────────────────────────────────────────────
#  VECTOR STORE  (ChromaDB — semantic retrieval)
# ──────────────────────────────────────────────
CHROMA_PATH       = str(BASE_DIR / "chroma_db")
CHROMA_COLLECTION = "journal_entries"
RAG_TOP_K         = 6                      # results returned per semantic query

# ──────────────────────────────────────────────
#  WINDOW
# ──────────────────────────────────────────────
WIN_W = 780
WIN_H = 580

# ──────────────────────────────────────────────
#  COLOUR PALETTE  (warm white + orange)
# ──────────────────────────────────────────────
BG       = "#FFF8F1"   # warm white background
BG_INPUT = "#FFFFFF"   # clean input/card surface
BG_HOVER = "#FFE8D1"   # gentle orange hover

FG       = "#2F241E"   # soft espresso text
FG_DIM   = "#8A6E5B"   # muted warm secondary text
FG_MID   = "#F28A2E"   # focus orange
FG_ERR   = "#C2412D"   # calm red error state
FG_AMBER = "#E66A1A"   # primary orange accent

BORDER   = "#F1C9A7"   # warm peach border

# ──────────────────────────────────────────────
#  TYPOGRAPHY
# ──────────────────────────────────────────────
F_TITLE   = ("Georgia", 24, "bold")
F_HEADING = ("Aptos", 12, "bold")
F_BODY    = ("Aptos", 11)
F_SMALL   = ("Aptos",  9)
F_LABEL   = ("Aptos", 10, "bold")
