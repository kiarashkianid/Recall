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
os.environ["OPENAI_API_KEY"] = (
    "sk-proj-C5l9FgbkVKnvo10NKCJS7z14E6aKyH3PHc9opHLrzumgzorO6ls_aIGy-"
    "glU2nKlHNQ3muD49wT3BlbkFJhqv4pByMXkGjG60nCDFOg1X1W8BiIYBu0vMvWrQO0_"
    "R2FMaChdY0HVyxK712vcs1efhUHChjYA"
)

# ──────────────────────────────────────────────
#  DATABASE
# ──────────────────────────────────────────────
DB_CONFIG: dict = {
    "dbname":   "journal_db",
    "user":     "postgres",
    "password": "1382",
    "host":     "localhost",
    "port":     "5432",
}

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
