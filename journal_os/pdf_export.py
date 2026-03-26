"""
pdf_export.py
─────────────
Generates a styled PDF from a summary string using reportlab.
No UI, no database calls, no AI logic.
"""

from datetime import datetime


# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────

def _esc(text: str) -> str:
    """Escape XML special characters for reportlab Paragraph."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def _is_section_header(line: str) -> bool:
    """Return True if the line looks like a section header (━ chars or ALL CAPS)."""
    return "━" in line or (line.isupper() and len(line) < 60)


# ──────────────────────────────────────────────
#  PUBLIC API
# ──────────────────────────────────────────────

def export_summary_pdf(summary_text: str, output_path: str) -> None:
    """
    Write a formatted PDF of the AI summary to output_path.

    Args:
        summary_text: The raw summary string from ai_summary.generate_summary().
        output_path:  Absolute or relative file path ending in .pdf.

    Raises:
        ImportError: If reportlab is not installed.
        Exception:   On any reportlab build error.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles    import ParagraphStyle
        from reportlab.lib.enums     import TA_LEFT, TA_CENTER
        from reportlab.platypus      import (SimpleDocTemplate, Paragraph,
                                             Spacer, HRFlowable)
        from reportlab.lib.units     import cm
        from reportlab.lib           import colors
    except ImportError:
        raise ImportError(
            "reportlab is required for PDF export.\n"
            "Install it with:  pip install reportlab"
        )

    # ── Colours ──
    C_GREEN      = colors.HexColor("#1A7A00")
    C_GREEN_DARK = colors.HexColor("#0D4D00")
    C_GREY       = colors.HexColor("#555555")
    C_GREY_LIGHT = colors.HexColor("#CCCCCC")
    C_BLACK      = colors.HexColor("#111111")

    # ── Paragraph styles ──
    sty_title = ParagraphStyle(
        "Title",
        fontName="Courier-Bold", fontSize=20,
        textColor=C_GREEN, spaceAfter=4, alignment=TA_LEFT,
    )
    sty_meta = ParagraphStyle(
        "Meta",
        fontName="Courier", fontSize=9,
        textColor=C_GREY, spaceAfter=18, alignment=TA_LEFT,
    )
    sty_section = ParagraphStyle(
        "Section",
        fontName="Courier-Bold", fontSize=12,
        textColor=C_GREEN_DARK, spaceBefore=16, spaceAfter=6,
    )
    sty_body = ParagraphStyle(
        "Body",
        fontName="Courier", fontSize=10,
        textColor=C_BLACK, leading=15, spaceAfter=5,
    )
    sty_footer = ParagraphStyle(
        "Footer",
        fontName="Courier", fontSize=8,
        textColor=C_GREY, spaceBefore=6, alignment=TA_CENTER,
    )

    # ── Document ──
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2.4*cm, rightMargin=2.4*cm,
        topMargin=2.8*cm,  bottomMargin=2.4*cm,
    )

    story = []

    # Header
    story.append(Paragraph("◈  JOURNAL OS — Weekly Summary", sty_title))
    story.append(Paragraph(
        f"Generated {datetime.now().strftime('%A, %B %d, %Y  ·  %H:%M')}",
        sty_meta,
    ))
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=C_GREEN_DARK, spaceAfter=12,
    ))

    # Body lines
    for line in summary_text.split("\n"):
        raw = line.strip()
        if not raw:
            story.append(Spacer(1, 0.2*cm))
            continue

        if _is_section_header(raw):
            header_text = raw.replace("━", "").strip()
            if header_text:
                story.append(HRFlowable(
                    width="100%", thickness=0.5,
                    color=C_GREY_LIGHT, spaceAfter=4,
                ))
                story.append(Paragraph(_esc(header_text), sty_section))
        else:
            story.append(Paragraph(_esc(raw), sty_body))

    # Footer
    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(
        width="100%", thickness=0.5,
        color=C_GREEN_DARK, spaceBefore=8,
    ))
    story.append(Paragraph(
        "Exported from JOURNAL OS v1.0  ·  Powered by CrewAI",
        sty_footer,
    ))

    doc.build(story)
