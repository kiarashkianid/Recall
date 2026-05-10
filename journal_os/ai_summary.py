"""
ai_summary.py
─────────────
RAG-agentic journal analysis powered by CrewAI + ChromaDB.

Architecture
────────────
                  ┌─────────────────────────────────┐
                  │          JournalAgent            │
                  │   (CrewAI Agent + LLM backend)   │
                  └──────────────┬──────────────────┘
                     calls tool  │  on each sub-question
                                 ▼
                  ┌─────────────────────────────────┐
                  │       search_journal (Tool)      │
                  │  semantic query → vector_store   │
                  │  returns top-K relevant chunks   │
                  └──────────────┬──────────────────┘
                                 ▼
                  ┌─────────────────────────────────┐
                  │         ChromaDB (local)         │
                  │  cosine similarity over all      │
                  │  embedded journal entries        │
                  └─────────────────────────────────┘

The agent is "agentic" because it decides *what* to search for.
It issues three targeted queries (highlights / learnings / patterns),
retrieves only semantically relevant chunks from the vector store,
and synthesises a structured report — never receiving all entries
blindly as in a naive prompt-stuffing approach.

Public API
──────────
    generate_summary()   → structured weekly report (str)
    answer_question()    → freeform Q&A against full journal (str)
"""

from html import escape

from crewai import Agent, Task, Crew
from crewai.tools import tool
from . import db
from . import vector_store
from .config import OPENAI_LLM_MODEL


SUMMARY_ENTRY_LIMIT = 12
SUMMARY_CONTEXT_CHAR_LIMIT = 12000
ENTRY_CHAR_LIMIT = 1800


# ──────────────────────────────────────────────
#  RAG TOOL  (shared by both public functions)
# ──────────────────────────────────────────────

@tool("search_journal")
def search_journal(query: str) -> str:
    """
    Semantic search over all personal journal entries.
    Use this tool to retrieve entries relevant to a specific topic,
    theme, emotion, or question before writing any analysis.

    Args:
        query: A focused natural-language question or topic phrase,
               e.g. 'key events and accomplishments this week' or
               'moments of anxiety or self-doubt'.

    Returns:
        The most semantically relevant journal excerpts as plain text.
    """
    hits = vector_store.query(query)
    return vector_store.format_hits(hits)


def _clip_text(text: str, limit: int) -> str:
    """Trim long journal text while preserving the beginning and ending."""
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean

    head = clean[: limit // 2].rstrip()
    tail = clean[-(limit // 2):].lstrip()
    return f"{head}\n...[middle trimmed for length]...\n{tail}"


def _format_summary_context(rows: list[tuple]) -> str:
    """Format recent entries as tagged evidence for the summary prompt."""
    blocks = []
    total = 0

    for entry_id, title, content, date in reversed(rows):
        body = _clip_text(str(content), ENTRY_CHAR_LIMIT)
        block = (
            f'<entry id="{entry_id}" date="{date}" '
            f'title="{escape(str(title), quote=True)}">\n'
            f"{escape(body, quote=False)}\n"
            "</entry>"
        )
        if blocks and total + len(block) > SUMMARY_CONTEXT_CHAR_LIMIT:
            break
        blocks.append(block)
        total += len(block)

    return "\n\n".join(blocks)


# ──────────────────────────────────────────────
#  AGENT FACTORY
# ──────────────────────────────────────────────

def _make_analyst(use_search: bool = True) -> Agent:
    return Agent(
        role="Personal Journal Analyst",
        goal=(
            "Turn recent journal entries into a specific, grounded reflection "
            "that helps the writer understand what mattered, what repeated, "
            "and what small next step is worth trying."
        ),
        backstory=(
            "You are a practical, perceptive journal analyst. You are warm "
            "without being sentimental, direct without being harsh, and you "
            "never diagnose, moralise, or invent facts. Every useful claim "
            "must be grounded in a specific journal entry."
        ),
        tools=[search_journal] if use_search else [],
        llm=OPENAI_LLM_MODEL,
        verbose=False,
    )


# ──────────────────────────────────────────────
#  PUBLIC: WEEKLY SUMMARY
# ──────────────────────────────────────────────

_SUMMARY_PROMPT_TEMPLATE = """\
You are writing a useful reflection from the user's most recent journal entries.

Primary evidence:
<recent_entries count="{entry_count}">
{entry_context}
</recent_entries>

Use the recent_entries block as the main source of truth.
{search_guidance}

Quality bar:
- Be specific to the entries. Mention dates or titles when useful.
- Prefer concrete observations over generic encouragement.
- Separate what happened from what you infer.
- Do not diagnose, moralise, exaggerate, or invent missing details.
- If evidence is thin, say so plainly instead of filling space.
- Keep the whole reflection readable in one screen: about 450-700 words.

Output format — use EXACTLY these section headers:

━━━ RECENT SNAPSHOT ━━━
Write 2-3 sentences on what this period seems to have been about.

━━━ MOMENTS THAT MATTERED ━━━
Write 3-5 bullets. Each bullet should name a concrete event, decision,
tension, or small win from the entries.

━━━ PATTERNS I NOTICE ━━━
Write 2-4 bullets. Each bullet should describe a repeated theme and include
brief evidence from more than one entry when available.

━━━ WHAT MAY NEED ATTENTION ━━━
Write 2-3 bullets about unresolved friction, avoided decisions, energy drains,
or needs that keep showing up. Keep this grounded and non-clinical.

━━━ ONE SMALL NEXT STEP ━━━
Suggest one low-friction action for the coming week, tied directly to the
entries. Make it practical enough to do in under 30 minutes.

━━━ A QUESTION TO SIT WITH ━━━
End with one thoughtful question that follows from the evidence.
"""


def generate_summary() -> str:
    """
    Run the RAG-agentic weekly analysis.

    The agent receives recent entries as primary evidence, may use semantic
    search when available, and synthesises a structured report.

    Returns:
        Multi-section reflection string.

    Raises:
        RuntimeError: If no journal entries exist.
        Exception:    Propagated from CrewAI / OpenAI on failure.
    """
    recent_entries = db.fetch_recent_entries_with_ids(SUMMARY_ENTRY_LIMIT)
    if not recent_entries:
        raise RuntimeError(
            "No journal entries found. Add an entry first, then generate a reflection."
        )

    try:
        search_available = vector_store.collection_size() > 0
    except Exception:
        search_available = False

    search_guidance = (
        "You may use search_journal for one or two targeted checks only when "
        "it would help confirm a theme or find an older related entry. Do not "
        "let older search results override the recent_entries block."
        if search_available else
        "Semantic search is not available for this run. Do not call tools; "
        "work only from the recent_entries block."
    )

    prompt = _SUMMARY_PROMPT_TEMPLATE.format(
        entry_count=len(recent_entries),
        entry_context=_format_summary_context(recent_entries),
        search_guidance=search_guidance,
    )

    analyst = _make_analyst(use_search=search_available)
    task    = Task(
        description=prompt,
        expected_output=(
            "A concise, evidence-grounded reflection with the exact requested "
            "section headers, concrete observations, one next step, and one "
            "question."
        ),
        agent=analyst,
    )
    crew   = Crew(agents=[analyst], tasks=[task], verbose=False)
    result = crew.kickoff()
    return str(result).strip()


# ──────────────────────────────────────────────
#  PUBLIC: FREEFORM Q&A
# ──────────────────────────────────────────────

_QA_PROMPT = """\
A user wants to query their personal journal. Their question is:

  "{question}"

Instructions:
1. Call search_journal with a query that best retrieves relevant entries.
2. If the first results seem incomplete, call search_journal again with
   a rephrased query.
3. Answer the user's question using ONLY the retrieved journal entries.
4. Be concise and specific. Quote or paraphrase directly from the entries.
5. If no relevant entries are found, say so clearly.
"""


def answer_question(question: str) -> str:
    """
    Answer a freeform question about the journal using RAG.

    The agent may call search_journal multiple times with different
    phrasings to gather enough context before answering.

    Args:
        question: Natural-language question from the user,
                  e.g. "What was I worried about last month?"

    Returns:
        A grounded answer derived from retrieved journal entries.

    Raises:
        RuntimeError: If the vector store is empty.
        Exception:    Propagated from CrewAI / OpenAI on failure.
    """
    if vector_store.collection_size() == 0:
        raise RuntimeError(
            "The vector store is empty. Add some journal entries first."
        )

    analyst = _make_analyst()
    task    = Task(
        description=_QA_PROMPT.format(question=question),
        expected_output=(
            "A concise, grounded answer to the user's question, "
            "based solely on retrieved journal entries."
        ),
        agent=analyst,
    )
    crew   = Crew(agents=[analyst], tasks=[task], verbose=False)
    result = crew.kickoff()
    return str(result).strip()
