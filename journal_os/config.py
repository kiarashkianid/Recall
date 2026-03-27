"""
config.py
─────────
Single source of truth for every constant in Journal OS.
Edit DB credentials, API key, and theme values here.
"""

import os

# ──────────────────────────────────────────────
#  API
# ──────────────────────────────────────────────
OPENAI_API_KEY = (
    "my last brain cell"
)
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_LLM_MODEL       = "gpt-4o"

# ──────────────────────────────────────────────
#  DATABASE  (PostgreSQL — structured storage)
# ──────────────────────────────────────────────
DB_CONFIG: dict = {
    "dbname":   "journal_db",
    "user":     "postgres",
    "password": "1382",
    "host":     "localhost",
    "port":     "5432",
}

# ──────────────────────────────────────────────
#  VECTOR STORE  (ChromaDB — semantic retrieval)
# ──────────────────────────────────────────────
CHROMA_PATH       = "./chroma_db"          # persisted on disk next to the project
CHROMA_COLLECTION = "journal_entries"
RAG_TOP_K         = 6                      # results returned per semantic query

# ──────────────────────────────────────────────
#  WINDOW
# ──────────────────────────────────────────────
WIN_W = 780
WIN_H = 580

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
