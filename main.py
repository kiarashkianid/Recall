"""Convenience launcher for the Recall desktop app."""


def main() -> None:
    try:
        from journal_os.main import main as run_app
    except ModuleNotFoundError as ex:
        missing = ex.name or "a required module"
        if missing == "tkinter":
            install_hint = "Install Tkinter first, e.g. `sudo apt-get install python3-tk`."
        else:
            install_hint = "Install Python dependencies with `python3 -m pip install -r requirements.txt`."
        raise SystemExit(f"Missing dependency: {missing}\n{install_hint}") from ex

    run_app()


if __name__ == "__main__":
    main()
