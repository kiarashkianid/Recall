"""
ui/chrome.py
────────────
Builds and owns the persistent app shell:
  • top header bar (title + live clock)
  • swappable content area
  • bottom status bar (message + mode label)

Nothing about journal data or screens lives here.
"""

import tkinter as tk
from datetime import datetime
from journal_os.config import BG, BORDER, FG, FG_DIM, FG_ERR, F_TITLE, F_SMALL
from ui.widgets import make_separator


class AppChrome:
    """
    Mixin that sets up the window chrome on top of a tk.Tk root.
    Subclasses get:
        self.content     – tk.Frame to place screen widgets into
        self._status()   – update the bottom status bar
        self._mode()     – update the mode label (top-right)
        self._clear()    – destroy all children of self.content
    """

    def build_chrome(self) -> None:
        """Call once from __init__ after configuring the root window."""
        self._build_header()
        make_separator(self.root).pack(fill="x")
        self._build_content_area()
        make_separator(self.root).pack(fill="x")
        self._build_status_bar()

    # ──────────────────────────────────────────────
    #  PRIVATE BUILDERS
    # ──────────────────────────────────────────────

    def _build_header(self) -> None:
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill="x")

        left = tk.Frame(hdr, bg=BG)
        left.pack(side="left", padx=24, pady=16)
        tk.Label(left, text="Recall", font=F_TITLE, bg=BG, fg=FG).pack(anchor="w")
        tk.Label(
            left,
            text="A calm place to write and reflect",
            font=F_SMALL,
            bg=BG,
            fg=FG_DIM,
        ).pack(anchor="w", pady=(2, 0))

        right = tk.Frame(hdr, bg=BG)
        right.pack(side="right", padx=24)
        self._clock_lbl = tk.Label(right, text="", font=F_SMALL, bg=BG, fg=FG_DIM)
        self._clock_lbl.pack()
        self._tick()

    def _build_content_area(self) -> None:
        self.content = tk.Frame(self.root, bg=BG)
        self.content.pack(fill="both", expand=True, padx=32, pady=18)

    def _build_status_bar(self) -> None:
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x")

        self._status_lbl = tk.Label(
            bar, text="Status: Ready",
            font=F_SMALL, bg=BG, fg=FG_DIM,
            anchor="w", padx=24, pady=8,
        )
        self._status_lbl.pack(side="left")

        self._mode_lbl = tk.Label(
            bar, text="HOME",
            font=F_SMALL, bg=BG, fg=FG_DIM,
            anchor="e", padx=24,
        )
        self._mode_lbl.pack(side="right")

    # ──────────────────────────────────────────────
    #  CLOCK
    # ──────────────────────────────────────────────

    def _tick(self) -> None:
        self._clock_lbl.config(text=datetime.now().strftime("%b %d, %Y  %H:%M"))
        self.root.after(1000, self._tick)

    # ──────────────────────────────────────────────
    #  PUBLIC CHROME API
    # ──────────────────────────────────────────────

    def _clear(self) -> None:
        """Destroy all widgets inside the content frame."""
        for widget in self.content.winfo_children():
            widget.destroy()

    def _status(self, message: str, err: bool = False) -> None:
        """Update the bottom-left status label."""
        colour = FG_ERR if err else FG_DIM
        self._status_lbl.config(text=f"Status: {message}", fg=colour)

    def _mode(self, label: str) -> None:
        """Update the bottom-right mode label."""
        self._mode_lbl.config(text=label)
