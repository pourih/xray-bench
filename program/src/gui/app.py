"""GUI Application entry point for xray-bench."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure program directory is in sys.path
program_dir = Path(__file__).resolve().parent.parent.parent
if str(program_dir) not in sys.path:
    sys.path.insert(0, str(program_dir))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from src.config import load_config
from src.gui.main_window import MainWindow
from src.gui.theme import get_stylesheet


def get_asset_path(filename: str) -> Optional[Path]:
    """Resolve asset file path across project root and program directory."""
    candidates = [
        program_dir.parent / "assets" / filename,
        program_dir / "assets" / filename,
        Path("assets") / filename,
    ]
    for p in candidates:
        if p.is_file():
            return p.resolve()
    return None


def main() -> None:
    # Set Windows AppUserModelID so taskbar groups properly with custom icon
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("xbench.proxy.benchmark")
        except Exception:
            pass

    # High-DPI support
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("xBench")
    app.setOrganizationName("xBench")

    # Set Application Icon globally
    icon_path = get_asset_path("icon.png")
    if icon_path:
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)

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
