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
#  COLOUR PALETTE  (warm parchment & ink)
# ──────────────────────────────────────────────
BG       = "#F5F1EB"   # warm cream — main background
BG_INPUT = "#EDE8DF"   # slightly deeper cream — inputs
BG_HOVER = "#E4DDD1"   # muted sand — button hover

FG       = "#2C2825"   # warm charcoal — primary text
FG_DIM   = "#8A7F73"   # warm grey-brown — labels / status
FG_MID   = "#5C7A64"   # muted sage — focus borders / accents
FG_ERR   = "#A33B2A"   # terracotta — error state
FG_AMBER = "#8A6020"   # warm honey — accent / export button

BORDER   = "#C8BFB2"   # warm stone — default border


# ──────────────────────────────────────────────
#  TYPOGRAPHY
# ──────────────────────────────────────────────
F_TITLE   = ("Courier New", 22, "bold")
F_HEADING = ("Courier New", 12, "bold")
F_BODY    = ("Courier New", 11)
F_SMALL   = ("Courier New",  9)
F_LABEL   = ("Courier New", 10)