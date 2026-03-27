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

from crewai import Agent, Task, Crew
from crewai.tools import tool
import vector_store
from config import OPENAI_LLM_MODEL


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


# ──────────────────────────────────────────────
#  AGENT FACTORY
# ──────────────────────────────────────────────

def _make_analyst() -> Agent:
    return Agent(
        role="Personal Journal Analyst",
        goal=(
            "Retrieve and analyse relevant journal entries using the "
            "search_journal tool, then produce an honest and insightful report."
        ),
        backstory=(
            "You are a perceptive journal analyst. You never fabricate "
            "information — every claim must come from a retrieved journal entry. "
            "You use the search_journal tool to pull targeted context before "
            "drawing any conclusion."
        ),
        tools=[search_journal],
        llm=OPENAI_LLM_MODEL,
        verbose=False,
    )


# ──────────────────────────────────────────────
#  PUBLIC: WEEKLY SUMMARY
# ──────────────────────────────────────────────

_SUMMARY_PROMPT = """\
You are analysing a personal journal. Use the search_journal tool to
retrieve relevant entries for each of the three sections below, then
write the final report.

Follow these steps in order:
1. Call search_journal("key events highlights experiences this week")
2. Call search_journal("lessons learned realisations insights growth")
3. Call search_journal("recurring themes emotions mood patterns thoughts")
4. Write the report using ONLY what you retrieved. Never invent details.

Output format — use EXACTLY these section headers:

━━━ WEEKLY HIGHLIGHTS ━━━
Key events, moments, and experiences. Be specific. Bullet list.

━━━ WHAT I LEARNED ━━━
Explicit and implicit lessons, realisations, insights. Bullet list.

━━━ PATTERNS & REFLECTIONS ━━━
Recurring themes, emotions, or thought patterns observed.

If a section has no supporting evidence from the entries, write:
  "Not mentioned in recent entries."
"""


def generate_summary() -> str:
    """
    Run the RAG-agentic weekly analysis.

    The agent issues three targeted semantic searches, retrieves
    relevant chunks from ChromaDB, and synthesises a structured report.

    Returns:
        Three-section summary string.

    Raises:
        RuntimeError: If the vector store is empty.
        Exception:    Propagated from CrewAI / OpenAI on failure.
    """
    if vector_store.collection_size() == 0:
        raise RuntimeError(
            "The vector store is empty. "
            "Add journal entries first — they are embedded automatically on save."
        )

    analyst = _make_analyst()
    task    = Task(
        description=_SUMMARY_PROMPT,
        expected_output=(
            "A structured three-section report with headers: "
            "WEEKLY HIGHLIGHTS, WHAT I LEARNED, PATTERNS & REFLECTIONS."
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