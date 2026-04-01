"""
config.py
─────────
Single source of truth for every constant in Journal OS.

Credentials are loaded from a .env file (via python-dotenv) so they
never need to live in source code. Copy .env.example → .env and fill
in your values. Hard-coded fallbacks are provided for non-sensitive
defaults only.

Install:  pip install python-dotenv
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (the directory containing this file)
load_dotenv(Path(__file__).parent / ".env")


# ──────────────────────────────────────────────
#  API
# ──────────────────────────────────────────────
OPENAI_API_KEY         = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_LLM_MODEL       = os.getenv("OPENAI_LLM_MODEL", "gpt-4o")

# Make available to libraries that read the env var directly
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


# ──────────────────────────────────────────────
#  DATABASE  (PostgreSQL — structured storage)
# ──────────────────────────────────────────────
DB_CONFIG: dict = {
    "dbname":   os.getenv("DB_NAME",     "journal_db"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     os.getenv("DB_PORT",     "5432"),
}


# ──────────────────────────────────────────────
#  VECTOR STORE  (ChromaDB — semantic retrieval)
# ──────────────────────────────────────────────
CHROMA_PATH       = os.getenv("CHROMA_PATH",  "./chroma_db")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "journal_entries")
RAG_TOP_K         = int(os.getenv("RAG_TOP_K", "6"))


# ──────────────────────────────────────────────
#  WINDOW
# ──────────────────────────────────────────────
WIN_W = 820
WIN_H = 620


# ──────────────────────────────────────────────
#  COLOUR PALETTE  (phosphor-green terminal)
# ──────────────────────────────────────────────
BG       = "#080808"   # near-black background
BG_INPUT = "#0F0F0F"   # slightly lighter input bg
BG_HOVER = "#0A1A0A"   # button hover bg

FG       = "#39FF14"   # phosphor green — primary text
FG_DIM   = "#1C6E0A"   # muted green — labels / status
FG_MID   = "#27B006"   # mid green — focus borders
FG_ERR   = "#FF4040"   # red — error state
FG_AMBER = "#FFB000"   # amber — accent / export button

BORDER   = "#1A5C0A"   # default border colour


# ──────────────────────────────────────────────
#  TYPOGRAPHY
# ──────────────────────────────────────────────
F_TITLE   = ("Courier New", 22, "bold")
F_HEADING = ("Courier New", 12, "bold")
F_BODY    = ("Courier New", 11)
F_SMALL   = ("Courier New",  9)
F_LABEL   = ("Courier New", 10)