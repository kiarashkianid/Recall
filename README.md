# Recall

# ◈ Journal OS

> A minimalist retro-terminal personal journal with AI-powered weekly analysis and PDF export.

---

## What It Does

Journal OS is a local desktop app for writing and reviewing daily journal entries. At the end of each week, a single button runs an AI agent that reads your last 7 days of writing and produces a structured summary covering your highlights, what you learned, and patterns in your thinking. That summary can be exported as a formatted PDF.

No cloud sync. No accounts. Everything lives in a local PostgreSQL database on your machine.

---

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| **UI** | [Tkinter](https://docs.python.org/3/library/tkinter.html) | Native Python GUI — window, widgets, event loop |
| **Database** | [PostgreSQL](https://www.postgresql.org/) | Stores all journal entries persistently |
| **DB Driver** | [psycopg2](https://www.psycopg.org/) | Python ↔ PostgreSQL connector |
| **AI Orchestration** | [CrewAI](https://github.com/joaomdmoura/crewAI) | Defines and runs the AI analyst agent |
| **LLM Backend** | [OpenAI GPT-4](https://platform.openai.com/) | Powers the agent's reasoning (via CrewAI) |
| **PDF Generation** | [ReportLab](https://www.reportlab.com/) | Renders the styled summary PDF |

---

## Project Structure

```
journal_os/
│
├── main.py           ← Entry point. Composes the app and starts the Tk loop.
├── config.py         ← All constants: DB credentials, API key, colours, fonts.
├── db.py             ← Database layer: schema setup and all CRUD queries.
├── ai_summary.py     ← AI layer: CrewAI agent definition and prompt logic.
├── pdf_export.py     ← PDF layer: ReportLab document generation.
│
└── ui/
    ├── __init__.py
    ├── widgets.py    ← Reusable widget factories (button, entry, text, etc.).
    ├── chrome.py     ← Persistent app shell: header, clock, status bar.
    └── screens.py    ← All screen logic: Home, Add Entry, View, AI Summary.
```

Each file has a single responsibility. The UI layer never queries the database directly — it calls `db.py`. The screens never call CrewAI directly — they call `ai_summary.py`. PDF generation is fully isolated in `pdf_export.py`.

---

## Setup

### 1. Prerequisites

- Python 3.11+
- PostgreSQL running locally (default port 5432)
- An OpenAI API key

### 2. Create the database

```sql
CREATE DATABASE journal_db;
```

### 3. Install dependencies

```bash
pip install psycopg2-binary crewai reportlab
```

### 4. Configure credentials

Open `config.py` and update:

```python
DB_CONFIG = {
    "dbname":   "journal_db",
    "user":     "your_pg_user",
    "password": "your_pg_password",
    "host":     "localhost",
    "port":     "5432",
}

os.environ["OPENAI_API_KEY"] = "sk-..."
```

### 5. Run

```bash
python main.py
```

---

## How the AI Summary Works

When you press **Generate Summary**, the app:

1. Queries PostgreSQL for all entries from the past 7 days.
2. Passes the combined text to a CrewAI `Agent` configured as a personal journal analyst.
3. The agent uses OpenAI GPT-4 to produce a structured three-section report:
   - **Weekly Highlights** — key events and experiences
   - **What I Learned** — explicit and implicit insights
   - **Patterns & Reflections** — recurring themes or emotions
4. The result is displayed in the terminal-style output panel.
5. Optionally exported to a formatted PDF via **Export PDF**.

The agent is instructed never to invent information — it only summarises what is explicitly written in your entries.

---

## Design Notes

The UI uses a phosphor-green-on-black terminal aesthetic throughout — `Courier New` monospace font, `#39FF14` neon green on `#080808` near-black, box-drawing characters (`┌─┐`) for entry borders, and a live clock in the header. No third-party UI framework is used; everything is plain Tkinter.
