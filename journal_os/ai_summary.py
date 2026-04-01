"""
ai_summary.py
─────────────
RAG-agentic journal analysis powered by CrewAI + ChromaDB.

Architecture
────────────
    JournalAgent (CrewAI)
        │  calls tool on each sub-question
        ▼
    search_journal (Tool)  →  vector_store.query()  →  ChromaDB
        │
        └─► top-K relevant chunks returned to agent
            └─► GPT-4o synthesises report from retrieved context only

The agent is "agentic" because it decides *what* to search for and
can issue multiple queries before writing. It never receives all entries
blindly — only semantically relevant chunks.

Public API
──────────
    generate_summary(start, end)  →  structured weekly/custom report (str)
    answer_question(question)     →  freeform Q&A against full journal (str)
"""

from crewai import Agent, Task, Crew
from crewai.tools import tool
from logger import get_logger
import vector_store
from config import OPENAI_LLM_MODEL

log = get_logger(__name__)


# ──────────────────────────────────────────────
#  RAG TOOL
# ──────────────────────────────────────────────

@tool("search_journal")
def search_journal(query: str) -> str:
    """
    Semantic search over all personal journal entries.
    Use this to retrieve entries relevant to a specific topic, theme,
    emotion, or question before writing any analysis.

    Args:
        query: A focused natural-language question or topic phrase.

    Returns:
        The most semantically relevant journal excerpts as plain text.
    """
    hits = vector_store.query(query)
    return vector_store.format_hits(hits)


# ──────────────────────────────────────────────
#  AGENT FACTORY
# ──────────────────────────────────────────────

def _make_analyst() -> Agent:
    return Agent(
        role="Personal Journal Analyst",
        goal=(
            "Retrieve and analyse relevant journal entries using the "
            "search_journal tool, then produce an honest, insightful report."
        ),
        backstory=(
            "You are a perceptive journal analyst. You never fabricate "
            "information — every claim must come from a retrieved journal entry. "
            "You use search_journal to pull targeted context before drawing "
            "any conclusion, and re-query with different terms if results are thin."
        ),
        tools=[search_journal],
        llm=OPENAI_LLM_MODEL,
        verbose=False,
    )


# ──────────────────────────────────────────────
#  PUBLIC: SUMMARY (with configurable date range)
# ──────────────────────────────────────────────

_SUMMARY_PROMPT = """\
You are analysing a personal journal for the period {start} to {end}.
Use the search_journal tool to retrieve relevant entries for each section,
then write the final report.

Follow these steps in order:
1. Call search_journal("key events highlights experiences {date_hint}")
2. Call search_journal("lessons learned realisations insights growth")
3. Call search_journal("recurring themes emotions mood patterns thoughts")
4. Write the report using ONLY what you retrieved. Never invent details.

Output format — use EXACTLY these section headers:

━━━ HIGHLIGHTS  ({start} → {end}) ━━━
Key events, moments, and experiences. Bullet list. Be specific.

━━━ WHAT I LEARNED ━━━
Explicit and implicit lessons, realisations, insights. Bullet list.

━━━ PATTERNS & REFLECTIONS ━━━
Recurring themes, emotions, or thought patterns observed.

If a section has no supporting evidence, write:
  "Not mentioned in this period's entries."
"""


def generate_summary(start: str, end: str) -> str:
    """
    Run the RAG-agentic analysis for a given date range.

    Args:
        start: ISO date string 'YYYY-MM-DD' (inclusive).
        end:   ISO date string 'YYYY-MM-DD' (inclusive).

    Returns:
        Three-section structured summary string.

    Raises:
        RuntimeError: If the vector store is empty.
        Exception:    Propagated from CrewAI / OpenAI.
    """
    if vector_store.collection_size() == 0:
        raise RuntimeError(
            "The vector store is empty. "
            "Add journal entries first — they embed automatically on save."
        )

    log.info("Generating summary  start=%s  end=%s", start, end)
    date_hint = f"between {start} and {end}"

    analyst = _make_analyst()
    task    = Task(
        description=_SUMMARY_PROMPT.format(start=start, end=end, date_hint=date_hint),
        expected_output=(
            "A structured three-section report: "
            "HIGHLIGHTS, WHAT I LEARNED, PATTERNS & REFLECTIONS."
        ),
        agent=analyst,
    )
    crew   = Crew(agents=[analyst], tasks=[task], verbose=False)
    result = str(crew.kickoff()).strip()
    log.info("Summary generated  chars=%d", len(result))
    return result


# ──────────────────────────────────────────────
#  PUBLIC: FREEFORM Q&A
# ──────────────────────────────────────────────

_QA_PROMPT = """\
A user wants to query their personal journal. Their question is:

  "{question}"

Instructions:
1. Call search_journal with a query that best retrieves relevant entries.
2. If the first results seem incomplete or off-topic, call search_journal
   again with a rephrased or narrower query (up to 3 attempts).
3. Answer using ONLY the retrieved journal entries.
4. Be concise and specific. Quote or paraphrase directly from entries.
5. If no relevant entries are found after searching, say so clearly.
6. End with: "Sources: [date · title, date · title, ...]" listing the
   entries you drew from.
"""


def answer_question(question: str) -> str:
    """
    Answer a freeform question about the journal using RAG.

    The agent may call search_journal multiple times with different phrasings.

    Args:
        question: Natural-language question, e.g. "What was I stressed about?"

    Returns:
        A grounded answer with source attribution.

    Raises:
        RuntimeError: If the vector store is empty.
        Exception:    Propagated from CrewAI / OpenAI.
    """
    if vector_store.collection_size() == 0:
        raise RuntimeError("The vector store is empty. Add some journal entries first.")

    log.info("Answering question: %r", question[:80])
    analyst = _make_analyst()
    task    = Task(
        description=_QA_PROMPT.format(question=question),
        expected_output=(
            "A concise, grounded answer with source attribution, "
            "based solely on retrieved journal entries."
        ),
        agent=analyst,
    )
    crew   = Crew(agents=[analyst], tasks=[task], verbose=False)
    result = str(crew.kickoff()).strip()
    log.info("Q&A answer generated  chars=%d", len(result))
    return result