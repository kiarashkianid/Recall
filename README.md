# Recall AI 
## Demo :  https://www.youtube.com/watch?v=moRR7oqqqiM
> A minimalist retro-terminal personal journal with semantic search,
> AI-powered weekly analysis, freeform journal Q&A, and PDF export.

---
## What It Does

Journal OS is a local desktop app for writing and reviewing daily journal
entries. Every entry you save is automatically embedded into a local vector
database (ChromaDB). At the end of each week, an AI agent semantically
searches your writing and produces a structured summary. You can also ask
your journal any freeform question and get a grounded, cited answer.

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| **UI** | [Tkinter](https://docs.python.org/3/library/tkinter.html) | Native Python GUI — window, widgets, event loop |
| **Structured storage** | [PostgreSQL](https://www.postgresql.org/) | Persists all journal entries (title, content, date) |
| **DB driver** | [psycopg2](https://www.psycopg.org/) | Python ↔ PostgreSQL connector |
| **Vector store** | [ChromaDB](https://www.trychroma.com/) | Local persistent vector DB for semantic retrieval |
| **Embeddings** | [OpenAI text-embedding-3-small](https://platform.openai.com/docs/guides/embeddings) | Converts journal text to dense vectors |
| **AI orchestration** | [CrewAI](https://github.com/joaomdmoura/crewAI) | Agent, Task, Crew; exposes `search_journal` as a tool |
| **LLM backend** | [OpenAI GPT-4o](https://platform.openai.com/) | Reasoning and synthesis inside the agent |
| **PDF generation** | [ReportLab](https://www.reportlab.com/) | Renders the styled summary PDF |

---

## Project Structure

```
journal_os/
│
├── main.py             ← Entry point. Bootstraps DB, syncs vectors, starts UI.
├── config.py           ← All constants: credentials, model names, ChromaDB path,
│                         colours, fonts. Edit only this file to reconfigure.
│
├── db.py               ← PostgreSQL layer: schema, insert, fetch queries.
│                         Returns entry IDs so the caller can embed immediately.
│
├── vector_store.py     ← ChromaDB wrapper: upsert, semantic query, bulk sync.
│                         Pure retrieval logic — no AI, no UI.
│
├── ai_summary.py       ← RAG-agentic layer: CrewAI agent + search_journal tool.
│                         Exposes generate_summary() and answer_question().
│
├── pdf_export.py       ← ReportLab PDF generation. Takes a string, writes a file.
│
└── ui/
    ├── __init__.py
    ├── widgets.py       ← Stateless widget factories (button, entry, text, etc.).
    ├── chrome.py        ← Persistent app shell: header, live clock, status bar.
    └── screens.py       ← All four screens. Calls db/vector_store/ai_summary —
                           never touches SQL or AI directly.
```

### Dependency graph

```
main.py
  ├── db.py              (PostgreSQL)
  ├── vector_store.py    (ChromaDB)
  └── ui/
        ├── chrome.py
        └── screens.py
              ├── db.py
              ├── vector_store.py
              ├── ai_summary.py  →  vector_store.py (RAG tool)
              └── pdf_export.py

config.py  ←  imported by everything
```

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
python3 -m pip install -r requirements.txt
```

On Debian/Ubuntu, Tkinter is provided by the system package manager:

```bash
sudo apt-get install python3-pip python3-tk
```

### 4. Configure credentials

Copy the template to a local `.env` file and fill in your credentials:

```bash
cp .env.example .env
```

```dotenv
OPENAI_API_KEY=sk-...
POSTGRES_DB=journal_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_pg_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

You can also set the same values in your shell:

```bash
export OPENAI_API_KEY="sk-..."
export POSTGRES_DB="journal_db"
export POSTGRES_USER="postgres"
export POSTGRES_PASSWORD="your_pg_password"
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
```

### 5. Run

```bash
python3 main.py
```

On first launch, any existing PostgreSQL entries are synced into ChromaDB
automatically (idempotent upsert). After that, every new entry is embedded
the moment you press Save.

---

## How the RAG Agent Works

```
User presses [ GENERATE SUMMARY ]
        │
        ▼
  App loads the most recent journal entries from PostgreSQL
        │
        ▼
  Agent receives a grounded reflection task with those entries as evidence
        │
        ├─► Optional: search_journal(...) for a targeted theme check
        │         └─► ChromaDB cosine search → relevant older chunks
        │
        └─► GPT-4o synthesises from recent entries first
                  └─► Reflection: Snapshot / Moments / Patterns /
                       Attention / Next Step / Question
```

If semantic search is unavailable, Generate can still create a reflection
from the recent PostgreSQL entries. The **Ask** feature still requires
ChromaDB because it answers open-ended questions through semantic search.

```
User asks a question
        │
        └─► Tool call: search_journal(...)
        │         └─► ChromaDB cosine search → top-6 relevant chunks
                  └─► GPT-4o answers from retrieved context only
```

---
