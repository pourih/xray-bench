"""GUI Application entry point for xray-bench."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure program directory is in sys.path
program_dir = Path(__file__).resolve().parent.parent.parent
if str(program_dir) not in sys.path:
    sys.path.insert(0, str(program_dir))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from src.config import load_config
from src.gui.main_window import MainWindow
from src.gui.theme import get_stylesheet


def main() -> None:
    # High-DPI support
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("xBench")
    app.setOrganizationName("xBench")

    # Set Default Font
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # Apply modern stylesheet from config
    try:
        cfg = load_config()
        theme = getattr(cfg.general, "theme", "dark")
    except Exception:
        theme = "dark"

    app.setStyleSheet(get_stylesheet(theme))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
