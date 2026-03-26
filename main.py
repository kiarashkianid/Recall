"""
main.py
───────
Entry point for Journal OS.

Composes AppChrome + Screens into JournalApp,
bootstraps the database schema, and starts the Tk event loop.
"""

import tkinter as tk
from tkinter import messagebox

import db
from config import BG, WIN_W, WIN_H
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
        self.root.title("JOURNAL OS")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self._init_db()
        self.build_chrome()   # AppChrome: header + content area + status bar
        self.show_home()      # Screens: render the home menu

    def _init_db(self) -> None:
        try:
            db.setup_schema()
        except Exception as ex:
            messagebox.showerror("Database Error",
                                 f"Cannot connect to PostgreSQL:\n\n{ex}")


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
