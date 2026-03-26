"""
ai_summary.py
─────────────
CrewAI-powered journal analysis.
Accepts a formatted journal string and returns a structured text report.
No UI, no database calls, no file I/O.
"""

from crewai import Agent, Task, Crew


# ──────────────────────────────────────────────
#  PROMPT TEMPLATE
# ──────────────────────────────────────────────

_PROMPT = """\
Analyse the following personal journal entries from the past 7 days.
Produce a clean, structured report with EXACTLY three sections:

━━━ WEEKLY HIGHLIGHTS ━━━
List the key events, moments, and experiences mentioned. Be specific.

━━━ WHAT I LEARNED ━━━
Extract explicit and implicit lessons, realisations, or insights.

━━━ PATTERNS & REFLECTIONS ━━━
Identify any recurring themes, emotions, or thought patterns.

─────────────────────────────────────
JOURNAL ENTRIES:
{journal_text}
─────────────────────────────────────

RULES:
• Only use information present in the entries above.
• If a section has nothing relevant, write "Not mentioned."
• Keep language clear and factual. No filler phrases.
"""


# ──────────────────────────────────────────────
#  PUBLIC API
# ──────────────────────────────────────────────

def generate_summary(journal_text: str) -> str:
    """
    Run the CrewAI analyst on the provided journal text.

    Args:
        journal_text: Pre-formatted string of entries from db.fetch_last_week_entries().

    Returns:
        A three-section analysis string.

    Raises:
        Exception: Propagated from CrewAI / OpenAI on failure.
    """
    analyst = Agent(
        role="Personal Journal Analyst",
        goal="Extract meaningful insights from personal journal entries",
        backstory=(
            "You are a thoughtful and perceptive journal analyst. "
            "You read personal journal entries carefully and extract "
            "highlights, learnings, and emotional patterns — never "
            "inventing information that isn't there."
        ),
        verbose=False,
    )

    task = Task(
        description=_PROMPT.format(journal_text=journal_text),
        expected_output=(
            "A structured three-section analysis: "
            "Weekly Highlights, What I Learned, Patterns & Reflections."
        ),
        agent=analyst,
    )

    crew = Crew(
        agents=[analyst],
        tasks=[task],
        verbose=False,
    )

    result = crew.kickoff()
    return str(result).strip()
