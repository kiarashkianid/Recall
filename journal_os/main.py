"""
main.py
───────
Entry point for Journal OS.

Startup sequence:
  1. Setup PostgreSQL schema (idempotent).
  2. Sync all existing entries into ChromaDB (idempotent upsert).
  3. Build the Tkinter window and launch the event loop.
"""

import tkinter as tk
from tkinter import messagebox

from . import db
from . import vector_store
from .config import BG, WIN_W, WIN_H
from ui.chrome  import AppChrome
from ui.screens import Screens


class JournalApp(AppChrome, Screens):
    """
    Top-level application class.
    Inherits the persistent shell from AppChrome and all screen
    logic from Screens. Its own __init__ is the only glue needed.
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Recall Journal")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self._init_db()
        self._sync_vectors()
        self.build_chrome()   # AppChrome → header + content area + status bar
        self.show_home()      # Screens   → render the home menu

    def _init_db(self) -> None:
        try:
            db.setup_schema()
        except Exception as ex:
            messagebox.showerror(
                "Database Error",
                f"Cannot connect to PostgreSQL:\n\n{ex}"
            )

    def _sync_vectors(self) -> None:
        """
        Upsert all existing PostgreSQL entries into ChromaDB.
        Safe to call every startup — upsert is idempotent.
        Runs synchronously before the window opens (usually < 1 s).
        """
        try:
            entries = db.fetch_all_entries_with_ids()
            if entries:
                vector_store.sync_from_postgres(entries)
        except Exception as ex:
            # Non-fatal: the app still works, RAG features will warn separately
            print(f"[vector sync] warning: {ex}")


# ──────────────────────────────────────────────
#  BOOTSTRAP
# ──────────────────────────────────────────────

def main() -> None:
    root = tk.Tk()

    # Centre on screen
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{WIN_W}x{WIN_H}+{(sw - WIN_W) // 2}+{(sh - WIN_H) // 2}")

    JournalApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
