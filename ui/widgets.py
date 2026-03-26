"""
ui/widgets.py
─────────────
Stateless factory functions that create styled Tkinter widgets.
Every function returns the widget without packing it — callers decide layout.
"""

import tkinter as tk
from tkinter import scrolledtext
from journal_os.config import (
    BG, BG_INPUT, BG_HOVER,
    FG, FG_DIM, FG_MID, FG_AMBER, BORDER,
    F_HEADING, F_BODY, F_LABEL,
)


def make_button(
    parent: tk.Widget,
    text: str,
    command,
    width: int = 26,
    accent: bool = False,
) -> tk.Button:
    """
    Retro-styled flat button with hover glow.

    Args:
        parent:  Tkinter parent widget.
        text:    Button label.
        command: Callback on click.
        width:   Character width.
        accent:  If True, use amber colour instead of green.
    """
    fg_col = FG_AMBER if accent else FG

    btn = tk.Button(
        parent,
        text=text,
        command=command,
        font=F_HEADING,
        bg=BG, fg=fg_col,
        activebackground=BG_HOVER,
        activeforeground=fg_col,
        relief="flat", bd=0,
        cursor="hand2",
        width=width, pady=9,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=FG,
    )
    btn.bind("<Enter>", lambda _: btn.config(bg=BG_HOVER, highlightbackground=FG_MID))
    btn.bind("<Leave>", lambda _: btn.config(bg=BG,       highlightbackground=BORDER))
    return btn


def make_label(
    parent: tk.Widget,
    text: str,
    font=None,
    fg: str | None = None,
    **kw,
) -> tk.Label:
    """Plain label with theme defaults."""
    return tk.Label(
        parent,
        text=text,
        font=font or F_LABEL,
        bg=BG,
        fg=fg or FG_DIM,
        **kw,
    )


def make_entry(parent: tk.Widget, width: int = 58) -> tk.Entry:
    """Single-line text entry with focus-glow border."""
    entry = tk.Entry(
        parent,
        font=F_BODY,
        width=width,
        bg=BG_INPUT, fg=FG,
        insertbackground=FG,
        relief="flat",
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=FG,
    )
    entry.bind("<FocusIn>",  lambda _: entry.config(highlightbackground=FG_MID))
    entry.bind("<FocusOut>", lambda _: entry.config(highlightbackground=BORDER))
    return entry


def make_text(parent: tk.Widget, height: int = 9) -> tk.Text:
    """Multi-line text box with focus-glow border."""
    text = tk.Text(
        parent,
        font=F_BODY,
        bg=BG_INPUT, fg=FG,
        insertbackground=FG,
        relief="flat",
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=FG,
        height=height,
        wrap="word",
        padx=10, pady=8,
        selectbackground="#003300",
        selectforeground=FG,
    )
    text.bind("<FocusIn>",  lambda _: text.config(highlightbackground=FG_MID))
    text.bind("<FocusOut>", lambda _: text.config(highlightbackground=BORDER))
    return text


def make_scrolltext(parent: tk.Widget, height: int = 18) -> scrolledtext.ScrolledText:
    """Read-only-friendly scrollable text area."""
    st = scrolledtext.ScrolledText(
        parent,
        font=F_BODY,
        bg=BG_INPUT, fg=FG,
        insertbackground=FG,
        relief="flat",
        highlightthickness=1,
        highlightbackground=BORDER,
        height=height,
        wrap="word",
        padx=10, pady=8,
        selectbackground="#003300",
        selectforeground=FG,
    )
    st.vbar.config(
        bg=BG,
        troughcolor=BG_INPUT,
        activebackground=FG_DIM,
        width=8,
    )
    return st


def make_separator(parent: tk.Widget) -> tk.Frame:
    """1-pixel horizontal rule in the border colour."""
    return tk.Frame(parent, height=1, bg=BORDER)
