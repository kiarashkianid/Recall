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

from journal_os import db
from journal_os import vector_store
from journal_os import ai_summary
from journal_os import pdf_export
from journal_os.config import BG, FG, FG_DIM, FG_AMBER, FG_ERR, BORDER, F_HEADING, F_SMALL
from ui.widgets import (
    make_button, make_label, make_entry,
    make_text, make_scrolltext,
)


class Screens:
    """
    Mixin providing all four screen methods.
    Navigation is done by calling self.show_*(). Each screen starts
    with self._clear() to wipe the previous screen's widgets.
    """

    # ──────────────────────────────────────────────
    #  HOME
    # ──────────────────────────────────────────────

    def show_home(self) -> None:
        self._clear()
        self._mode("HOME")
        self._status("Ready")

        tk.Frame(self.content, bg=BG, height=24).pack()
        make_label(self.content, "What would you like to do today?",
                   font=("Aptos", 14, "bold"), fg=FG).pack()
        make_label(self.content, "Write, browse, or ask your journal for a little perspective.",
                   font=F_SMALL, fg=FG_DIM).pack(pady=(6, 18))

        menu = [
            ("Add a new entry",       self.show_add,     True),
            ("View past entries",     self.show_view,    False),
            ("Weekly reflection",     self.show_summary, False),
            ("Close Recall",          self.root.quit,    False),
        ]
        for text, cmd, accent in menu:
            make_button(self.content, text, cmd, width=30, accent=accent).pack(pady=5)

        tk.Frame(self.content, bg=BG, height=20).pack()

        # Show vector store status
        try:
            n = vector_store.collection_size()
            vec_msg = f"{n} journal embeddings indexed"
        except Exception:
            vec_msg = "AI search is not configured yet"

        make_label(self.content, vec_msg, font=F_SMALL, fg=FG_DIM).pack()
        make_label(self.content, "Local journal storage with optional AI reflection",
                   font=F_SMALL, fg=FG_DIM).pack()

    # ──────────────────────────────────────────────
    #  ADD ENTRY
    # ──────────────────────────────────────────────

    def show_add(self) -> None:
        self._clear()
        self._mode("ADD ENTRY")
        self._status("Take your time. Save when it feels complete.")

        make_label(self.content, "New journal entry",
                   font=F_HEADING, fg=FG).pack(anchor="w", pady=(0, 14))

        # ── Row: Title + Date ──
        row = tk.Frame(self.content, bg=BG)
        row.pack(fill="x", pady=(0, 10))

        left_col = tk.Frame(row, bg=BG)
        left_col.pack(side="left", fill="x", expand=True, padx=(0, 20))
        make_label(left_col, "Title").pack(anchor="w")
        title_e = make_entry(left_col, width=42)
        title_e.pack(fill="x", pady=(3, 0))
        title_e.focus()

        right_col = tk.Frame(row, bg=BG)
        right_col.pack(side="right")
        make_label(right_col, "Date (YYYY-MM-DD)").pack(anchor="w")
        date_e = make_entry(right_col, width=16)
        date_e.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_e.pack(pady=(3, 0))

        # ── Content ──
        make_label(self.content, "Entry").pack(anchor="w", pady=(6, 3))
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
                self._status("Please fill in the title, date, and entry.", err=True)
                return
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                self._status("Date must use YYYY-MM-DD.", err=True)
                return

            try:
                # Save to PostgreSQL and get the new row's id
                new_id = db.insert_entry_returning_id(title, content, date)
            except Exception as ex:
                self._status(f"Could not save entry: {ex}", err=True)
                return

            try:
                # Immediately embed into ChromaDB
                self._status("Saving and preparing AI search...")
                vector_store.upsert_entry(new_id, title, content, date)
                self._status(f"Entry saved and indexed (id={new_id})")
            except Exception as ex:
                self._status(f"Entry saved; AI indexing skipped: {ex}", err=True)
                messagebox.showwarning(
                    "Embedding Skipped",
                    "The entry was saved to PostgreSQL, but semantic embedding failed.\n\n"
                    f"{ex}"
                )

            self.show_home()

        make_button(btn_row, "Save entry", _save, width=16, accent=True).pack(side="left", padx=(0, 10))
        make_button(btn_row, "Back", self.show_home, width=12).pack(side="left")

    # ──────────────────────────────────────────────
    #  VIEW ALL
    # ──────────────────────────────────────────────

    def show_view(self) -> None:
        self._clear()
        self._mode("VIEW ENTRIES")

        make_label(self.content, "Past entries",
                   font=F_HEADING, fg=FG).pack(anchor="w", pady=(0, 10))

        out = make_scrolltext(self.content, height=19)
        out.pack(fill="both", expand=True, pady=(0, 10))

        try:
            rows = db.fetch_all_entries()

            if not rows:
                out.insert("end", "\n  No entries yet.\n")
                self._status("0 entries in database")
            else:
                for title, content, date in rows:
                    out.insert("end",
                        f"\n  {date}  |  {title}\n"
                        f"  {'-'*64}\n"
                        f"  {content}\n"
                    )
                self._status(f"{len(rows)} entr{'y' if len(rows) == 1 else 'ies'} found")

        except Exception as ex:
            out.insert("end", f"\n  Could not load entries: {ex}")
            self._status(f"DB error: {ex}", err=True)

        out.config(state="disabled")
        make_button(self.content, "Back", self.show_home, width=12).pack(anchor="w")

    # ──────────────────────────────────────────────
    #  SUMMARY + RAG Q&A — screen setup
    # ──────────────────────────────────────────────

    def show_summary(self) -> None:
        self._clear()
        self._mode("AI SUMMARY + RAG Q&A")
        self._status("Generate a weekly reflection or ask your journal a question.")

        self._summary_text: str = ""

        # ── Section header ──
        make_label(self.content, "Reflection and questions",
                   font=F_HEADING, fg=FG).pack(anchor="w", pady=(0, 8))

        # ── Output area ──
        self._sum_out = make_scrolltext(self.content, height=14)
        self._sum_out.pack(fill="both", expand=True, pady=(0, 8))
        self._sum_out.insert("end",
            "\n  Create a gentle weekly reflection from your journal entries.\n\n"
            "  You can also ask a question about anything you have written,\n"
            "  and Recall will answer from your saved entries.\n"
        )
        self._sum_out.config(state="disabled")

        # ── Q&A input row ──
        qa_row = tk.Frame(self.content, bg=BG)
        qa_row.pack(fill="x", pady=(0, 6))

        make_label(qa_row, "Ask", fg=FG_DIM).pack(side="left", padx=(0, 8))
        self._qa_entry = make_entry(qa_row, width=52)
        self._qa_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._qa_entry.bind("<Return>", lambda _: self._launch_qa())

        self._ask_btn = make_button(
            qa_row, "Ask",
            self._launch_qa, width=10,
        )
        self._ask_btn.pack(side="left")

        # ── Action buttons ──
        btn_row = tk.Frame(self.content, bg=BG)
        btn_row.pack(fill="x")

        self._run_btn = make_button(
            btn_row, "Generate reflection",
            self._launch_summary, width=22, accent=True,
        )
        self._run_btn.pack(side="left", padx=(0, 10))

        self._export_btn = make_button(
            btn_row, "Export PDF",
            self._do_export_pdf, width=16, accent=True,
        )
        self._export_btn.pack(side="left", padx=(0, 10))
        self._export_btn.config(
            state="disabled", fg=FG_DIM,
            highlightbackground=BORDER,
        )

        make_button(btn_row, "Back", self.show_home, width=10).pack(side="left")

    # ──────────────────────────────────────────────
    #  SUMMARY — AI thread lifecycle
    # ──────────────────────────────────────────────

    def _launch_summary(self) -> None:
        self._run_btn.config(state="disabled", text="Reflecting...", fg=FG_DIM)
        self._ask_btn.config(state="disabled")
        self._status("Reading your entries and preparing a reflection...")
        self._summary_text = ""

        self._sum_out.config(state="normal")
        self._sum_out.delete("1.0", "end")
        self._sum_out.insert("end",
            "\n  Reading relevant entries...\n"
            "  Looking for highlights, lessons, and patterns...\n"
            "  Writing your reflection...\n\n"
            "  This may take 30-60 seconds.\n"
        )
        self._sum_out.config(state="disabled")

        threading.Thread(target=self._run_summary_ai, daemon=True).start()

    def _run_summary_ai(self) -> None:
        try:
            result = ai_summary.generate_summary()
            self._summary_text = result
            self._push_output(result, is_summary=True)
        except Exception as ex:
            self._push_output(f"  ERROR: {ex}", is_summary=False)
            self.root.after(0, lambda: self._status(f"Error: {ex}", err=True))

    # ──────────────────────────────────────────────
    #  Q&A — thread lifecycle
    # ──────────────────────────────────────────────

    def _launch_qa(self) -> None:
        question = self._qa_entry.get().strip()
        if not question:
            self._status("Type a question first.", err=True)
            return

        self._ask_btn.config(state="disabled", text="...", fg=FG_DIM)
        self._run_btn.config(state="disabled")
        self._status(f"Searching journal for: {question[:50]}...")

        self._sum_out.config(state="normal")
        self._sum_out.delete("1.0", "end")
        self._sum_out.insert("end",
            f"\n  Question: {question}\n\n"
            "  Finding relevant entries...\n"
            "  Writing an answer...\n"
        )
        self._sum_out.config(state="disabled")

        threading.Thread(
            target=self._run_qa_ai,
            args=(question,),
            daemon=True,
        ).start()

    def _run_qa_ai(self, question: str) -> None:
        try:
            answer = ai_summary.answer_question(question)
            output = f"Q: {question}\n\n{'-'*60}\n\n{answer}"
            self._push_output(output, is_summary=False)
        except Exception as ex:
            self._push_output(f"  ERROR: {ex}", is_summary=False)
            self.root.after(0, lambda: self._status(f"Error: {ex}", err=True))

    # ──────────────────────────────────────────────
    #  SHARED OUTPUT UPDATER (thread-safe)
    # ──────────────────────────────────────────────

    def _push_output(self, text: str, is_summary: bool) -> None:
        """Schedule a UI update back on the main Tk thread."""
        def _update():
            self._sum_out.config(state="normal")
            self._sum_out.delete("1.0", "end")
            self._sum_out.insert("end", "\n" + text + "\n")
            self._sum_out.config(state="disabled")

            # Re-enable buttons
            self._run_btn.config(state="normal", text="Generate reflection", fg="#FFFFFF")
            self._ask_btn.config(state="normal",  text="Ask", fg=FG)

            # Enable PDF export only after a successful summary
            if is_summary and self._summary_text and "ERROR" not in text[:20]:
                self._export_btn.config(state="normal", fg="#FFFFFF", highlightbackground=BORDER)
            self._status("Done")

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
            self._status(f"PDF saved: {path}")
            messagebox.showinfo("Export Complete", f"Summary saved to:\n{path}")
        except ImportError as ex:
            messagebox.showerror("Missing Package", str(ex))
        except Exception as ex:
            self._status(f"PDF error: {ex}", err=True)
            messagebox.showerror("Export Error", str(ex))
