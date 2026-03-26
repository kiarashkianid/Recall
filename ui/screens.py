"""
ui/screens.py
─────────────
All screen rendering and screen-level event handlers.
Implemented as a mixin so JournalApp can inherit chrome + screens cleanly.

Depends on:
    self.root       – tk.Tk  (from JournalApp)
    self.content    – tk.Frame (from AppChrome)
    self._clear()   – (from AppChrome)
    self._status()  – (from AppChrome)
    self._mode()    – (from AppChrome)
"""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

from journal_os import ai_summary, db, pdf_export
from journal_os.config import BG, FG, FG_DIM, FG_AMBER, BORDER, F_HEADING, F_SMALL
from ui.widgets import (
    make_button, make_label, make_entry,
    make_text, make_scrolltext,
)


class Screens:
    """
    Mixin providing all screen methods.
    Navigation is done by calling self._show_*(). Each screen starts
    with self._clear() to wipe the previous screen's widgets.
    """

    # ──────────────────────────────────────────────
    #  HOME
    # ──────────────────────────────────────────────

    def show_home(self) -> None:
        self._clear()
        self._mode("HOME")
        self._status("READY")

        tk.Frame(self.content, bg=BG, height=30).pack()
        make_label(self.content, "// SELECT OPERATION",
                   font=("Courier New", 10), fg=FG_DIM).pack()
        tk.Frame(self.content, bg=BG, height=22).pack()

        menu = [
            ("[ 01 ]  ADD NEW ENTRY",    self.show_add,     False),
            ("[ 02 ]  VIEW ALL ENTRIES", self.show_view,    False),
            ("[ 03 ]  WEEKLY AI SUMMARY",self.show_summary, False),
            ("[ 04 ]  EXIT",             self.root.quit,    True),
        ]
        for text, cmd, accent in menu:
            make_button(self.content, text, cmd, width=34, accent=accent).pack(pady=4)

        tk.Frame(self.content, bg=BG, height=30).pack()
        make_label(self.content, "JOURNAL OS  ·  powered by CrewAI",
                   font=F_SMALL, fg=FG_DIM).pack()

    # ──────────────────────────────────────────────
    #  ADD ENTRY
    # ──────────────────────────────────────────────

    def show_add(self) -> None:
        self._clear()
        self._mode("ADD ENTRY")
        self._status("Fill in fields and press SAVE")

        make_label(self.content, "// ADD JOURNAL ENTRY",
                   font=F_HEADING, fg=FG).pack(anchor="w", pady=(0, 14))

        # ── Row: Title + Date ──
        row = tk.Frame(self.content, bg=BG)
        row.pack(fill="x", pady=(0, 10))

        left_col = tk.Frame(row, bg=BG)
        left_col.pack(side="left", fill="x", expand=True, padx=(0, 20))
        make_label(left_col, "TITLE").pack(anchor="w")
        title_e = make_entry(left_col, width=42)
        title_e.pack(fill="x", pady=(3, 0))
        title_e.focus()

        right_col = tk.Frame(row, bg=BG)
        right_col.pack(side="right")
        make_label(right_col, "DATE  (YYYY-MM-DD)").pack(anchor="w")
        date_e = make_entry(right_col, width=16)
        date_e.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_e.pack(pady=(3, 0))

        # ── Content ──
        make_label(self.content, "CONTENT").pack(anchor="w", pady=(6, 3))
        content_t = make_text(self.content, height=10)
        content_t.pack(fill="x")

        # ── Buttons ──
        tk.Frame(self.content, bg=BG, height=12).pack()
        btn_row = tk.Frame(self.content, bg=BG)
        btn_row.pack(anchor="w")

        def _save():
            title   = title_e.get().strip()
            date    = date_e.get().strip()
            content = content_t.get("1.0", "end").strip()

            if not all([title, date, content]):
                self._status("ERROR: All fields are required", err=True)
                return
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                self._status("ERROR: Date must be YYYY-MM-DD", err=True)
                return

            try:
                db.insert_entry(title, content, date)
                self._status("ENTRY SAVED  ✓")
                self.show_home()
            except Exception as ex:
                self._status(f"DB ERROR: {ex}", err=True)

        make_button(btn_row, "[ SAVE ENTRY ]", _save,           width=16).pack(side="left", padx=(0, 10))
        make_button(btn_row, "[ ← BACK ]",     self.show_home,  width=12).pack(side="left")

    # ──────────────────────────────────────────────
    #  VIEW ALL
    # ──────────────────────────────────────────────

    def show_view(self) -> None:
        self._clear()
        self._mode("VIEW ENTRIES")

        make_label(self.content, "// JOURNAL ENTRIES",
                   font=F_HEADING, fg=FG).pack(anchor="w", pady=(0, 10))

        out = make_scrolltext(self.content, height=19)
        out.pack(fill="both", expand=True, pady=(0, 10))

        try:
            rows = db.fetch_all_entries()

            if not rows:
                out.insert("end", "\n  No entries found.\n")
                self._status("0 entries in database")
            else:
                for title, content, date in rows:
                    out.insert("end",
                        f"\n  ┌{'─'*62}\n"
                        f"  │  {date}   ·   {title}\n"
                        f"  ├{'─'*62}\n"
                        f"  │  {content}\n"
                        f"  └{'─'*62}\n"
                    )
                self._status(f"{len(rows)} entr{'y' if len(rows) == 1 else 'ies'} found")

        except Exception as ex:
            out.insert("end", f"\n  ERROR: {ex}")
            self._status(f"DB error: {ex}", err=True)

        out.config(state="disabled")
        make_button(self.content, "[ ← BACK ]", self.show_home, width=12).pack(anchor="w")

    # ──────────────────────────────────────────────
    #  SUMMARY — screen setup
    # ──────────────────────────────────────────────

    def show_summary(self) -> None:
        self._clear()
        self._mode("AI SUMMARY")
        self._status("Press GENERATE to analyse last 7 days")

        # Persistent state for this screen
        self._summary_text: str = ""

        make_label(self.content, "// WEEKLY AI SUMMARY",
                   font=F_HEADING, fg=FG).pack(anchor="w", pady=(0, 10))

        self._sum_out = make_scrolltext(self.content, height=17)
        self._sum_out.pack(fill="both", expand=True, pady=(0, 10))
        self._sum_out.insert("end",
            "\n  ░  Awaiting analysis...\n\n"
            "  Press  [ GENERATE SUMMARY ]  to run the AI.\n"
        )
        self._sum_out.config(state="disabled")

        btn_row = tk.Frame(self.content, bg=BG)
        btn_row.pack(fill="x")

        self._run_btn = make_button(
            btn_row, "[ GENERATE SUMMARY ]",
            self._launch_summary, width=22,
        )
        self._run_btn.pack(side="left", padx=(0, 10))

        self._export_btn = make_button(
            btn_row, "[ EXPORT PDF ]",
            self._do_export_pdf, width=16, accent=True,
        )
        self._export_btn.pack(side="left", padx=(0, 10))
        self._export_btn.config(
            state="disabled", fg=FG_DIM,
            highlightbackground="#1A1A00",
        )

        make_button(btn_row, "[ ← BACK ]", self.show_home, width=10).pack(side="left")

    # ──────────────────────────────────────────────
    #  SUMMARY — AI thread lifecycle
    # ──────────────────────────────────────────────

    def _launch_summary(self) -> None:
        self._run_btn.config(state="disabled", text="[ PROCESSING... ]", fg=FG_DIM)
        self._status("Running AI analysis  ·  please wait...")
        self._summary_text = ""

        self._sum_out.config(state="normal")
        self._sum_out.delete("1.0", "end")
        self._sum_out.insert("end",
            "\n  ░░░  Fetching journal entries...\n"
            "  ░░░  Initialising AI agent...\n"
            "  ░░░  Analysing patterns...\n\n"
            "  This may take 30–60 seconds.\n"
        )
        self._sum_out.config(state="disabled")

        threading.Thread(target=self._run_ai, daemon=True).start()

    def _run_ai(self) -> None:
        """Runs on a background thread — no direct UI calls here."""
        try:
            journal_text = db.fetch_last_week_entries()
            if not journal_text:
                self._push_summary(
                    "  No journal entries found in the last 7 days.\n"
                    "  Add some entries first, then run the summary."
                )
                return
            result = ai_summary.generate_summary(journal_text)
            self._summary_text = result
            self._push_summary(result)
        except Exception as ex:
            self._push_summary(f"  ERROR: {ex}")
            self.root.after(0, lambda: self._status(f"Error: {ex}", err=True))

    def _push_summary(self, text: str) -> None:
        """Thread-safe: schedule UI update back on the main thread."""
        def _update():
            self._sum_out.config(state="normal")
            self._sum_out.delete("1.0", "end")
            self._sum_out.insert("end", "\n" + text + "\n")
            self._sum_out.config(state="disabled")

            self._run_btn.config(state="normal", text="[ REGENERATE ]", fg=FG)

            if self._summary_text and not self._summary_text.startswith("  ERROR"):
                self._export_btn.config(
                    state="normal", fg=FG_AMBER,
                    highlightbackground=BORDER,
                )
            self._status("Analysis complete  ✓")

        self.root.after(0, _update)

    # ──────────────────────────────────────────────
    #  PDF EXPORT
    # ──────────────────────────────────────────────

    def _do_export_pdf(self) -> None:
        if not self._summary_text:
            return

        path = filedialog.asksaveasfilename(
            title="Save Summary PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf")],
            initialfile=f"journal_summary_{datetime.now().strftime('%Y%m%d')}.pdf",
        )
        if not path:
            return

        try:
            pdf_export.export_summary_pdf(self._summary_text, path)
            self._status(f"PDF saved  ✓   {path}")
            messagebox.showinfo("Export Complete", f"Summary saved to:\n{path}")
        except ImportError as ex:
            messagebox.showerror("Missing Package", str(ex))
        except Exception as ex:
            self._status(f"PDF error: {ex}", err=True)
            messagebox.showerror("Export Error", str(ex))
