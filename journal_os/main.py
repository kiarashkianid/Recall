"""
main.py
───────
Entry point for Journal OS.

Startup sequence:
  1. Initialise logging.
  2. Setup PostgreSQL schema (idempotent).
  3. Incrementally sync new entries into ChromaDB (only new rows embedded).
  4. Build the Tkinter window and start the event loop.
"""

import tkinter as tk
from tkinter import messagebox

from logger import get_logger
import db
import vector_store
from config import BG, WIN_W, WIN_H
from ui.chrome  import AppChrome
from ui.screens import Screens

log = get_logger(__name__)


class JournalApp(AppChrome, Screens):
    """
    Top-level application class.
    Inherits the persistent shell from AppChrome and all screen
    logic from Screens. __init__ is the only glue needed.
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("JOURNAL OS")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self._bind_global_keys()
        self._init_db()
        self._sync_vectors()
        self.build_chrome()   # AppChrome: header + content area + status bar
        self.show_home()      # Screens: render the home menu

    # ──────────────────────────────────────────────
    #  KEYBOARD SHORTCUTS
    # ──────────────────────────────────────────────

    def _bind_global_keys(self) -> None:
        """App-wide keyboard shortcuts."""
        self.root.bind("<Escape>",   lambda _: self._go_home_if_safe())
        self.root.bind("<F1>",       lambda _: self.show_home())
        self.root.bind("<F2>",       lambda _: self.show_add())
        self.root.bind("<F3>",       lambda _: self.show_view())
        self.root.bind("<F4>",       lambda _: self.show_summary())
        self.root.bind("<F5>",       lambda _: self._force_resync())

    def _go_home_if_safe(self) -> None:
        """Escape navigates home (screens implement their own unsaved-change guards)."""
        self.show_home()

    def _force_resync(self) -> None:
        """F5: re-embed any entries that are missing from the vector store."""
        try:
            entries = db.fetch_all_entries_with_ids()
            n = vector_store.sync_incremental(entries)
            self._status(f"Re-sync complete  ·  {n} new embeddings")
        except Exception as ex:
            log.error("Force resync failed: %s", ex, exc_info=True)
            self._status(f"Resync error: {ex}", err=True)

    # ──────────────────────────────────────────────
    #  STARTUP
    # ──────────────────────────────────────────────

    def _init_db(self) -> None:
        try:
            db.setup_schema()
        except Exception as ex:
            log.critical("Cannot connect to PostgreSQL: %s", ex, exc_info=True)
            messagebox.showerror(
                "Database Error",
                f"Cannot connect to PostgreSQL:\n\n{ex}\n\n"
                "Check DB_* values in your .env file."
            )

    def _sync_vectors(self) -> None:
        """
        Incrementally embed any entries not yet in ChromaDB.
        Runs synchronously before the window opens (fast after first run).
        """
        try:
            entries = db.fetch_all_entries_with_ids()
            n = vector_store.sync_incremental(entries)
            if n:
                log.info("Startup embedded %d new entries", n)
        except Exception as ex:
            # Non-fatal: UI still works; RAG features warn when used
            log.warning("Vector sync warning: %s", ex)


# ──────────────────────────────────────────────
#  BOOTSTRAP
# ──────────────────────────────────────────────

def main() -> None:
    log.info("Journal OS starting")
    root = tk.Tk()

    # Centre on screen
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{WIN_W}x{WIN_H}+{(sw - WIN_W) // 2}+{(sh - WIN_H) // 2}")

    JournalApp(root)
    root.mainloop()
    log.info("Journal OS exited cleanly")


if __name__ == "__main__":
    main()