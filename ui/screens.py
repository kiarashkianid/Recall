"""
ui/screens.py
─────────────
All screen rendering and interaction logic as a mixin.

Screens
───────
  show_home()        — dashboard with live stats
  show_add()         — create a new entry (Ctrl+S to save, Esc to back)
  show_view()        — two-pane: searchable list + detail with Edit / Delete
  show_edit(id)      — pre-filled edit form, updates PG + vector store
  show_summary()     — RAG summary with custom date range + Q&A conversation history
  show_stats()       — full statistics screen

Each screen calls self._clear() first to wipe the previous one.
Navigation back is always self.show_home() or show_view() where appropriate.
"""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime, timedelta, date

from logger import get_logger
import db
import vector_store
import ai_summary
import pdf_export
from config import (
    BG, BG_INPUT, FG, FG_DIM, FG_MID, FG_AMBER, FG_ERR,
    BORDER, F_TITLE, F_HEADING, F_BODY, F_SMALL, F_LABEL,
)
from ui.widgets import (
    make_button, make_label, make_entry,
    make_text, make_scrolltext,
)

log = get_logger(__name__)


class Screens:

    # ═══════════════════════════════════════════════════════════
    #  HOME — stats dashboard
    # ═══════════════════════════════════════════════════════════

    def show_home(self) -> None:
        self._clear()
        self._mode("HOME")
        self._status("READY  ·  F2=Add  F3=View  F4=Summary  F5=Resync")

        tk.Frame(self.content, bg=BG, height=16).pack()
        make_label(self.content, "// SELECT OPERATION",
                   font=("Courier New", 10), fg=FG_DIM).pack()
        tk.Frame(self.content, bg=BG, height=14).pack()

        menu = [
            ("[ F2 ]  ADD NEW ENTRY",       self.show_add,     False),
            ("[ F3 ]  VIEW ALL ENTRIES",    self.show_view,    False),
            ("[ F4 ]  WEEKLY AI SUMMARY",   self.show_summary, False),
            ("[ F0 ]  STATISTICS",          self.show_stats,   False),
            ("[ F9 ]  EXIT",                self.root.quit,    True),
        ]
        for text, cmd, accent in menu:
            make_button(self.content, text, cmd, width=34, accent=accent).pack(pady=3)

        tk.Frame(self.content, bg=BG, height=18).pack()

        # ── Stats bar ──
        stats_frame = tk.Frame(self.content, bg=BG)
        stats_frame.pack()

        try:
            s = db.get_stats()
            n_vec = vector_store.collection_size()

            stats_line_1 = (
                f"entries: {s['total_entries']}   "
                f"words: {s['total_words']:,}   "
                f"streak: {s['streak_days']}d"
            )
            stats_line_2 = (
                f"most active: {s['most_active_day']}   "
                f"vectors indexed: {n_vec}"
            )
            make_label(stats_frame, stats_line_1, font=F_SMALL, fg=FG_DIM).pack()
            make_label(stats_frame, stats_line_2, font=F_SMALL, fg=FG_DIM).pack()
        except Exception as ex:
            make_label(stats_frame, f"stats unavailable: {ex}", font=F_SMALL, fg=FG_ERR).pack()

        tk.Frame(self.content, bg=BG, height=8).pack()
        make_label(self.content, "JOURNAL OS  ·  RAG-Agentic  ·  powered by CrewAI",
                   font=F_SMALL, fg=FG_DIM).pack()

    # ═══════════════════════════════════════════════════════════
    #  ADD — new entry form
    # ═══════════════════════════════════════════════════════════

    def show_add(self) -> None:
        self._show_entry_form(entry_id=None)

    # ═══════════════════════════════════════════════════════════
    #  EDIT — pre-filled entry form
    # ═══════════════════════════════════════════════════════════

    def show_edit(self, entry_id: int) -> None:
        self._show_entry_form(entry_id=entry_id)

    # ───────────────────────────────────────────
    #  Shared add / edit form
    # ───────────────────────────────────────────

    def _show_entry_form(self, entry_id: int | None) -> None:
        """
        Renders the entry form in either Add (entry_id=None) or Edit mode.
        In Edit mode, fields are pre-populated and Save calls UPDATE.
        """
        is_edit = entry_id is not None
        self._clear()
        self._mode("EDIT ENTRY" if is_edit else "ADD ENTRY")
        self._status("Ctrl+S to save  ·  Esc to go back")

        heading = f"// {'EDIT' if is_edit else 'ADD'} JOURNAL ENTRY"
        make_label(self.content, heading, font=F_HEADING, fg=FG).pack(anchor="w", pady=(0, 14))

        # Pre-load existing data
        prefill_title, prefill_content, prefill_date = "", "", datetime.now().strftime("%Y-%m-%d")
        if is_edit:
            row = db.get_entry_by_id(entry_id)
            if row is None:
                self._status(f"ERROR: entry id={entry_id} not found", err=True)
                self.show_view()
                return
            _, prefill_title, prefill_content, prefill_date_obj = row
            prefill_date = str(prefill_date_obj)

        # ── Title + Date row ──
        row_frame = tk.Frame(self.content, bg=BG)
        row_frame.pack(fill="x", pady=(0, 10))

        left_col = tk.Frame(row_frame, bg=BG)
        left_col.pack(side="left", fill="x", expand=True, padx=(0, 20))
        make_label(left_col, "TITLE").pack(anchor="w")
        title_e = make_entry(left_col, width=42)
        title_e.insert(0, prefill_title)
        title_e.pack(fill="x", pady=(3, 0))
        title_e.focus()

        right_col = tk.Frame(row_frame, bg=BG)
        right_col.pack(side="right")
        make_label(right_col, "DATE  (YYYY-MM-DD)").pack(anchor="w")
        date_e = make_entry(right_col, width=16)
        date_e.insert(0, prefill_date)
        date_e.pack(pady=(3, 0))

        # ── Content ──
        make_label(self.content, "CONTENT").pack(anchor="w", pady=(6, 3))
        content_t = make_text(self.content, height=10)
        if prefill_content:
            content_t.insert("1.0", prefill_content)
        content_t.pack(fill="x")

        # ── Word count indicator ──
        wc_lbl = make_label(self.content, "words: 0", font=F_SMALL, fg=FG_DIM)
        wc_lbl.pack(anchor="e", pady=(2, 0))

        def _update_wc(_event=None):
            text = content_t.get("1.0", "end").strip()
            count = len(text.split()) if text else 0
            wc_lbl.config(text=f"words: {count}")
        content_t.bind("<KeyRelease>", _update_wc)
        _update_wc()

        # ── Buttons ──
        tk.Frame(self.content, bg=BG, height=10).pack()
        btn_row = tk.Frame(self.content, bg=BG)
        btn_row.pack(anchor="w")

        def _save(_event=None):
            title   = title_e.get().strip()
            date_s  = date_e.get().strip()
            content = content_t.get("1.0", "end").strip()

            if not all([title, date_s, content]):
                self._status("ERROR: All fields are required", err=True)
                return
            try:
                datetime.strptime(date_s, "%Y-%m-%d")
            except ValueError:
                self._status("ERROR: Date must be YYYY-MM-DD", err=True)
                return

            try:
                if is_edit:
                    db.update_entry(entry_id, title, content, date_s)
                    vector_store.upsert_entry(entry_id, title, content, date_s)
                    self._status(f"ENTRY UPDATED  ✓  (id={entry_id})")
                    log.info("Entry updated via UI  id=%s", entry_id)
                    self.show_view()
                else:
                    new_id = db.insert_entry_returning_id(title, content, date_s)
                    vector_store.upsert_entry(new_id, title, content, date_s)
                    self._status(f"ENTRY SAVED + EMBEDDED  ✓  (id={new_id})")
                    log.info("Entry created via UI  id=%s", new_id)
                    self.show_home()
            except Exception as ex:
                log.error("Save entry failed: %s", ex, exc_info=True)
                self._status(f"ERROR: {ex}", err=True)

        save_label = "[ SAVE CHANGES ]" if is_edit else "[ SAVE ENTRY ]"
        save_btn = make_button(btn_row, save_label, _save, width=18)
        save_btn.pack(side="left", padx=(0, 10))

        back_target = self.show_view if is_edit else self.show_home
        make_button(btn_row, "[ ← BACK ]", back_target, width=12).pack(side="left")

        # Keyboard shortcut
        self.content.bind_all("<Control-s>", _save)
        self.root.bind("<Escape>", lambda _: back_target())

    # ═══════════════════════════════════════════════════════════
    #  VIEW — searchable two-pane list + detail
    # ═══════════════════════════════════════════════════════════

    def show_view(self) -> None:
        self._clear()
        self._mode("VIEW ENTRIES")
        self._status("Select an entry  ·  then Edit or Delete")

        # Load entries
        try:
            all_rows = db.fetch_all_entries_with_ids()   # (id, title, content, date)
        except Exception as ex:
            log.error("fetch_all_entries_with_ids failed: %s", ex, exc_info=True)
            make_label(self.content, f"DB ERROR: {ex}", fg=FG_ERR).pack(pady=20)
            make_button(self.content, "[ ← BACK ]", self.show_home).pack()
            return

        self._view_all_rows    = all_rows          # full dataset
        self._view_filtered    = list(all_rows)    # currently shown subset
        self._view_selected_id = None              # id of selected entry

        # ── Header row: title + search ──
        hdr = tk.Frame(self.content, bg=BG)
        hdr.pack(fill="x", pady=(0, 8))

        make_label(hdr, "// VIEW ENTRIES", font=F_HEADING, fg=FG).pack(side="left")

        sfr = tk.Frame(hdr, bg=BG)
        sfr.pack(side="right")
        make_label(sfr, "FILTER:", font=F_LABEL, fg=FG_DIM).pack(side="left", padx=(0, 6))
        self._search_e = make_entry(sfr, width=24)
        self._search_e.pack(side="left")
        self._search_e.bind("<KeyRelease>", self._on_search_change)

        # ── Two-pane area ──
        panes = tk.Frame(self.content, bg=BG)
        panes.pack(fill="both", expand=True, pady=(0, 8))

        # Left: listbox
        left = tk.Frame(panes, bg=BG)
        left.pack(side="left", fill="y", padx=(0, 14))

        self._count_lbl = make_label(
            left, f"ENTRIES [{len(all_rows)}]", font=F_LABEL, fg=FG_DIM
        )
        self._count_lbl.pack(anchor="w", pady=(0, 4))

        lb_border = tk.Frame(left, bg=BORDER, padx=1, pady=1)
        lb_border.pack(fill="y", expand=True)

        lb_inner = tk.Frame(lb_border, bg=BG_INPUT)
        lb_inner.pack(fill="both", expand=True)

        self._listbox = tk.Listbox(
            lb_inner,
            font=F_BODY, width=30, height=14,
            bg=BG_INPUT, fg=FG,
            selectbackground="#D6CCBF", selectforeground=FG,
            activestyle="none",
            relief="flat", bd=0,
            highlightthickness=0,
        )
        lb_scroll = tk.Scrollbar(lb_inner, orient="vertical",
                                 bg=BG, troughcolor=BG_INPUT, width=8)
        self._listbox.config(yscrollcommand=lb_scroll.set)
        lb_scroll.config(command=self._listbox.yview)
        lb_scroll.pack(side="right", fill="y")
        self._listbox.pack(side="left", fill="both", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_entry_select)

        # Right: detail pane
        right = tk.Frame(panes, bg=BG)
        right.pack(side="right", fill="both", expand=True)

        make_label(right, "ENTRY DETAIL", font=F_LABEL, fg=FG_DIM).pack(anchor="w", pady=(0, 4))
        self._detail_out = make_scrolltext(right, height=14)
        self._detail_out.pack(fill="both", expand=True)
        self._detail_out.insert("end", "\n  Select an entry from the list.")
        self._detail_out.config(state="disabled")

        # ── Action buttons ──
        btn_row = tk.Frame(self.content, bg=BG)
        btn_row.pack(fill="x")

        self._edit_btn = make_button(btn_row, "[ EDIT ]",   self._edit_selected, width=12)
        self._edit_btn.pack(side="left", padx=(0, 8))
        self._edit_btn.config(state="disabled", fg=FG_DIM, highlightbackground=BORDER)

        self._del_btn = make_button(btn_row, "[ DELETE ]", self._delete_selected, width=12)
        self._del_btn.pack(side="left", padx=(0, 8))
        self._del_btn.config(state="disabled", fg=FG_ERR, highlightbackground=BORDER)

        make_button(btn_row, "[ ← BACK ]", self.show_home, width=12).pack(side="left")

        # Populate
        self._populate_listbox(all_rows)
        self._status(f"{len(all_rows)} entr{'y' if len(all_rows)==1 else 'ies'} found")

    def _populate_listbox(self, rows: list[tuple]) -> None:
        """Fill the listbox from a (filtered) list of rows."""
        self._listbox.delete(0, "end")
        self._view_filtered = rows
        for entry_id, title, content, entry_date in rows:
            label = f" {entry_date}  {title[:22]}"
            self._listbox.insert("end", label)
        self._count_lbl.config(text=f"ENTRIES [{len(rows)}]")
        # Reset detail pane
        self._detail_out.config(state="normal")
        self._detail_out.delete("1.0", "end")
        self._detail_out.insert("end", "\n  Select an entry from the list.")
        self._detail_out.config(state="disabled")
        self._view_selected_id = None
        self._edit_btn.config(state="disabled", fg=FG_DIM)
        self._del_btn.config(state="disabled", fg=FG_ERR)

    def _on_search_change(self, _event=None) -> None:
        """Filter the listbox as the user types in the search field."""
        term = self._search_e.get().strip().lower()
        if not term:
            filtered = self._view_all_rows
        else:
            filtered = [
                r for r in self._view_all_rows
                if term in r[1].lower() or term in r[2].lower()
            ]
        self._populate_listbox(filtered)

    def _on_entry_select(self, _event=None) -> None:
        """Show the selected entry in the detail pane and enable action buttons."""
        sel = self._listbox.curselection()
        if not sel:
            return
        idx   = sel[0]
        row   = self._view_filtered[idx]
        entry_id, title, content, entry_date = row
        self._view_selected_id = entry_id

        self._detail_out.config(state="normal")
        self._detail_out.delete("1.0", "end")
        self._detail_out.insert("end",
            f"\n  ┌{'─'*52}\n"
            f"  │  DATE:   {entry_date}\n"
            f"  │  TITLE:  {title}\n"
            f"  ├{'─'*52}\n"
            f"  │\n"
        )
        # Wrap long content lines
        for line in content.split("\n"):
            self._detail_out.insert("end", f"  │  {line}\n")
        self._detail_out.insert("end", f"  └{'─'*52}\n")
        self._detail_out.config(state="disabled")

        self._edit_btn.config(state="normal", fg=FG)
        self._del_btn.config(state="normal",  fg=FG_ERR)

    def _edit_selected(self) -> None:
        if self._view_selected_id is not None:
            self.show_edit(self._view_selected_id)

    def _delete_selected(self) -> None:
        entry_id = self._view_selected_id
        if entry_id is None:
            return

        # Find the title for the confirm dialog
        row = next((r for r in self._view_filtered if r[0] == entry_id), None)
        title = row[1] if row else f"id={entry_id}"

        confirmed = messagebox.askyesno(
            "Confirm Delete",
            f"Permanently delete this entry?\n\n  {title}\n\n"
            "This cannot be undone.",
        )
        if not confirmed:
            return

        try:
            db.delete_entry(entry_id)
            vector_store.delete_entry(entry_id)
            self._status(f"Deleted entry: {title}")
            log.info("Entry deleted via UI  id=%s  title=%r", entry_id, title)
            # Refresh the view
            self.show_view()
        except Exception as ex:
            log.error("Delete failed  id=%s: %s", entry_id, ex, exc_info=True)
            self._status(f"ERROR: {ex}", err=True)

    # ═══════════════════════════════════════════════════════════
    #  SUMMARY — RAG agent with date range + Q&A history
    # ═══════════════════════════════════════════════════════════

    def show_summary(self) -> None:
        self._clear()
        self._mode("AI SUMMARY + Q&A")
        self._status("Set date range → GENERATE  ·  or type a question → ASK")

        self._summary_text: str = ""
        self._qa_history:   list[str] = []   # persists within this screen visit

        make_label(self.content, "// WEEKLY AI SUMMARY  +  ASK YOUR JOURNAL",
                   font=F_HEADING, fg=FG).pack(anchor="w", pady=(0, 6))

        # ── Date range selector ──
        date_row = tk.Frame(self.content, bg=BG)
        date_row.pack(fill="x", pady=(0, 6))

        make_label(date_row, "FROM:", fg=FG_DIM).pack(side="left", padx=(0, 6))
        default_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        self._start_e = make_entry(date_row, width=12)
        self._start_e.insert(0, default_start)
        self._start_e.pack(side="left", padx=(0, 14))

        make_label(date_row, "TO:", fg=FG_DIM).pack(side="left", padx=(0, 6))
        self._end_e = make_entry(date_row, width=12)
        self._end_e.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self._end_e.pack(side="left", padx=(0, 14))

        # Quick preset buttons
        for label, days in [("7d", 7), ("30d", 30), ("90d", 90)]:
            make_button(
                date_row, f"[{label}]",
                lambda d=days: self._set_date_preset(d),
                width=5,
            ).pack(side="left", padx=2)

        # ── Output area ──
        self._sum_out = make_scrolltext(self.content, height=12)
        self._sum_out.pack(fill="both", expand=True, pady=(6, 6))
        self._sum_out.insert("end",
            "\n  ░  RAG-Agentic mode.\n\n"
            "  ▸  Set a date range and press [ GENERATE SUMMARY ]\n"
            "     Agent issues targeted semantic searches, then synthesises:\n"
            "     Highlights  ·  What I Learned  ·  Patterns & Reflections\n\n"
            "  ▸  Type any question below and press [ ASK ]\n"
            "     Your Q&A history persists for the session.\n"
        )
        self._sum_out.config(state="disabled")

        # ── Q&A input row ──
        qa_row = tk.Frame(self.content, bg=BG)
        qa_row.pack(fill="x", pady=(0, 4))

        make_label(qa_row, "ASK:", fg=FG_DIM).pack(side="left", padx=(0, 8))
        self._qa_entry = make_entry(qa_row, width=46)
        self._qa_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._qa_entry.bind("<Return>", lambda _: self._launch_qa())

        self._ask_btn = make_button(qa_row, "[ ASK ]", self._launch_qa, width=10)
        self._ask_btn.pack(side="left", padx=(0, 6))

        self._clear_btn = make_button(qa_row, "[ CLEAR ]", self._clear_history, width=9)
        self._clear_btn.pack(side="left")

        # ── Bottom buttons ──
        btn_row = tk.Frame(self.content, bg=BG)
        btn_row.pack(fill="x")

        self._run_btn = make_button(
            btn_row, "[ GENERATE SUMMARY ]", self._launch_summary, width=22,
        )
        self._run_btn.pack(side="left", padx=(0, 8))

        self._export_btn = make_button(
            btn_row, "[ EXPORT PDF ]", self._do_export_pdf, width=15, accent=True,
        )
        self._export_btn.pack(side="left", padx=(0, 8))
        self._export_btn.config(state="disabled", fg=FG_DIM, highlightbackground=BORDER)

        make_button(btn_row, "[ ← BACK ]", self.show_home, width=10).pack(side="left")

    # ───────────────────────────────────────────
    #  Date preset helpers
    # ───────────────────────────────────────────

    def _set_date_preset(self, days: int) -> None:
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end   = datetime.now().strftime("%Y-%m-%d")
        self._start_e.delete(0, "end"); self._start_e.insert(0, start)
        self._end_e.delete(0, "end");   self._end_e.insert(0, end)

    def _get_date_range(self) -> tuple[str, str] | None:
        """Validate and return (start, end) strings or set status + return None."""
        start = self._start_e.get().strip()
        end   = self._end_e.get().strip()
        try:
            s = datetime.strptime(start, "%Y-%m-%d")
            e = datetime.strptime(end,   "%Y-%m-%d")
        except ValueError:
            self._status("ERROR: Dates must be YYYY-MM-DD", err=True)
            return None
        if s > e:
            self._status("ERROR: Start date must be before end date", err=True)
            return None
        return start, end

    # ───────────────────────────────────────────
    #  Summary lifecycle
    # ───────────────────────────────────────────

    def _launch_summary(self) -> None:
        dr = self._get_date_range()
        if dr is None:
            return
        start, end = dr

        self._run_btn.config(state="disabled", text="[ PROCESSING... ]", fg=FG_DIM)
        self._ask_btn.config(state="disabled")
        self._status(f"RAG agent running  ·  {start} → {end}...")
        self._summary_text = ""

        self._write_output(
            f"\n  ░░░  Analysing journal: {start} → {end}\n"
            "  ░░░  Agent issuing semantic searches...\n"
            "  ░░░  Retrieving relevant chunks...\n"
            "  ░░░  Synthesising report...\n\n"
            "  This may take 30–60 seconds.\n"
        )
        threading.Thread(
            target=self._run_summary_ai, args=(start, end), daemon=True
        ).start()

    def _run_summary_ai(self, start: str, end: str) -> None:
        try:
            result             = ai_summary.generate_summary(start, end)
            self._summary_text = result
            self._append_output(f"{'═'*60}\n  SUMMARY  {start} → {end}\n{'═'*60}\n\n{result}")
            self.root.after(0, lambda: (
                self._run_btn.config(state="normal", text="[ GENERATE SUMMARY ]", fg=FG),
                self._ask_btn.config(state="normal", text="[ ASK ]", fg=FG),
                self._export_btn.config(state="normal", fg=FG_AMBER, highlightbackground=BORDER),
                self._status("Summary complete  ✓"),
            ))
        except Exception as ex:
            log.error("Summary AI failed: %s", ex, exc_info=True)
            self._append_output(f"\n  ERROR: {ex}\n")
            self.root.after(0, lambda: (
                self._run_btn.config(state="normal", text="[ GENERATE SUMMARY ]", fg=FG),
                self._ask_btn.config(state="normal", text="[ ASK ]", fg=FG),
                self._status(f"Error: {ex}", err=True),
            ))

    # ───────────────────────────────────────────
    #  Q&A lifecycle
    # ───────────────────────────────────────────

    def _launch_qa(self) -> None:
        question = self._qa_entry.get().strip()
        if not question:
            self._status("Type a question first", err=True)
            return

        self._ask_btn.config(state="disabled", text="[ ... ]", fg=FG_DIM)
        self._run_btn.config(state="disabled")
        self._status(f"Searching: {question[:60]}...")

        # Show spinner in output without wiping existing history
        self._append_output(
            f"\n{'─'*60}\n"
            f"  Q: {question}\n"
            f"{'─'*60}\n"
            "  ░░░  Retrieving relevant entries...\n"
        )
        self._qa_entry.delete(0, "end")

        threading.Thread(
            target=self._run_qa_ai, args=(question,), daemon=True
        ).start()

    def _run_qa_ai(self, question: str) -> None:
        try:
            answer = ai_summary.answer_question(question)
            block  = f"\n  A: {answer}\n"
            self._qa_history.append(f"Q: {question}\n\nA: {answer}")
            self._append_output(block)
            self.root.after(0, lambda: (
                self._run_btn.config(state="normal", text="[ GENERATE SUMMARY ]", fg=FG),
                self._ask_btn.config(state="normal", text="[ ASK ]", fg=FG),
                self._status("Answer ready  ✓"),
            ))
        except Exception as ex:
            log.error("Q&A AI failed: %s", ex, exc_info=True)
            self._append_output(f"\n  ERROR: {ex}\n")
            self.root.after(0, lambda: (
                self._run_btn.config(state="normal", text="[ GENERATE SUMMARY ]", fg=FG),
                self._ask_btn.config(state="normal", text="[ ASK ]", fg=FG),
                self._status(f"Error: {ex}", err=True),
            ))

    # ───────────────────────────────────────────
    #  Output helpers (thread-safe)
    # ───────────────────────────────────────────

    def _write_output(self, text: str) -> None:
        """Replace the output area content (thread-safe)."""
        def _do():
            self._sum_out.config(state="normal")
            self._sum_out.delete("1.0", "end")
            self._sum_out.insert("end", text)
            self._sum_out.config(state="disabled")
        self.root.after(0, _do)

    def _append_output(self, text: str) -> None:
        """Append text to the output area and scroll to bottom (thread-safe)."""
        def _do():
            self._sum_out.config(state="normal")
            self._sum_out.insert("end", text)
            self._sum_out.see("end")
            self._sum_out.config(state="disabled")
        self.root.after(0, _do)

    def _clear_history(self) -> None:
        self._qa_history.clear()
        self._summary_text = ""
        self._write_output(
            "\n  ░  History cleared.\n\n"
            "  Generate a new summary or ask a question.\n"
        )
        self._export_btn.config(state="disabled", fg=FG_DIM, highlightbackground=BORDER)
        self._status("History cleared")

    # ───────────────────────────────────────────
    #  PDF Export
    # ───────────────────────────────────────────

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
            messagebox.showinfo("Export Complete", f"Saved to:\n{path}")
        except ImportError as ex:
            messagebox.showerror("Missing Package", str(ex))
        except Exception as ex:
            log.error("PDF export failed: %s", ex, exc_info=True)
            self._status(f"PDF error: {ex}", err=True)
            messagebox.showerror("Export Error", str(ex))

    # ═══════════════════════════════════════════════════════════
    #  STATS — full statistics screen
    # ═══════════════════════════════════════════════════════════

    def show_stats(self) -> None:
        self._clear()
        self._mode("STATISTICS")
        self._status("Journal statistics")

        make_label(self.content, "// JOURNAL STATISTICS",
                   font=F_HEADING, fg=FG).pack(anchor="w", pady=(0, 18))

        try:
            s     = db.get_stats()
            n_vec = vector_store.collection_size()
        except Exception as ex:
            make_label(self.content, f"ERROR: {ex}", fg=FG_ERR).pack()
            make_button(self.content, "[ ← BACK ]", self.show_home).pack(pady=10)
            return

        rows = [
            ("Total Entries",        str(s["total_entries"])),
            ("Total Words Written",  f"{s['total_words']:,}"),
            ("Avg Words / Entry",    str(round(s["total_words"] / max(s["total_entries"], 1)))),
            ("Current Streak",       f"{s['streak_days']} day{'s' if s['streak_days'] != 1 else ''}"),
            ("Most Active Day",      s["most_active_day"]),
            ("First Entry",          s["oldest_date"] or "—"),
            ("Latest Entry",         s["newest_date"] or "—"),
            ("Vectors Indexed",      str(n_vec)),
            ("Vector Coverage",      f"{round(n_vec / max(s['total_entries'], 1) * 100)}%"),
        ]

        col_w = 28
        for label, value in rows:
            row_f = tk.Frame(self.content, bg=BG)
            row_f.pack(fill="x", pady=3)
            make_label(row_f, f"  {label:<{col_w}}", font=F_BODY, fg=FG_DIM).pack(side="left")
            make_label(row_f, value, font=F_BODY, fg=FG).pack(side="left")

        tk.Frame(self.content, bg=BORDER, height=1).pack(fill="x", pady=14)
        make_button(self.content, "[ ← BACK ]", self.show_home, width=12).pack(anchor="w")