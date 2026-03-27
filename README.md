# ◈ Journal OS  —  RAG-Agentic Edition

> A minimalist retro-terminal personal journal with semantic search,
> AI-powered weekly analysis, freeform journal Q&A, and PDF export.

---
/1.png)
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
pip install psycopg2-binary chromadb openai crewai reportlab
```

### 4. Configure credentials

Open `config.py` and update:

```python
OPENAI_API_KEY = "sk-..."

DB_CONFIG = {
    "user":     "your_pg_user",
    "password": "your_pg_password",
    ...
}

CHROMA_PATH = "./chroma_db"   # where ChromaDB persists on disk
```

### 5. Run

```bash
python main.py
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
  Agent receives task: "Analyse the journal"
        │
        ├─► Tool call: search_journal("key events highlights this week")
        │         └─► ChromaDB cosine search → top-6 relevant chunks
        │
        ├─► Tool call: search_journal("lessons learned insights growth")
        │         └─► ChromaDB cosine search → top-6 relevant chunks
        │
        ├─► Tool call: search_journal("recurring themes emotions patterns")
        │         └─► ChromaDB cosine search → top-6 relevant chunks
        │
        └─► GPT-4o synthesises from retrieved context only
                  └─► Structured report: Highlights / Learnings / Patterns
```

The **Ask** feature follows the same pattern but for a single user question,
with the agent free to re-query with rephrased terms if the first results
are insufficient.

---
