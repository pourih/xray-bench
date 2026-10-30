"""Modern dark and light theme styling and QSS stylesheets for xBench GUI."""

DARK_STYLESHEET = """
/* Global Reset */
QWidget {
    background-color: #121316;
    color: #f3f4f6;
    font-family: "Segoe UI Variable Text", "Segoe UI", -apple-system, sans-serif;
    font-size: 13px;
    selection-background-color: #6366f1;
    selection-color: #ffffff;
}

/* Main Window */
QMainWindow {
    background-color: #121316;
}

/* Sidebar Navigation */
#sidebar {
    background-color: #18191e;
    border-right: 1px solid #23252d;
    min-width: 210px;
    max-width: 210px;
}

#sidebarTitle {
    font-size: 19px;
    font-weight: 800;
    color: #ffffff;
    padding: 18px 16px 14px 16px;
    letter-spacing: -0.5px;
}

/* Navigation Buttons */
QPushButton.nav-btn {
    background-color: transparent;
    color: #9ca3af;
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    margin: 2px 8px;
}

QPushButton.nav-btn:hover {
    background-color: #23252d;
    color: #ffffff;
}

QPushButton.nav-btn:checked {
    background-color: #2e303d;
    color: #818cf8;
    font-weight: 600;
    border-left: 3px solid #6366f1;
}

/* Card Containers */
QFrame.card {
    background-color: #1a1c22;
    border: 1px solid #282a35;
    border-radius: 12px;
}

QFrame.card-highlight {
    background-color: #1e2028;
    border: 1px solid #3b3e4f;
    border-radius: 12px;
}

/* Headers & Labels */
QLabel.heading-1 {
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
}

QLabel.heading-2 {
    font-size: 15px;
    font-weight: 600;
    color: #e5e7eb;
}

QLabel.label-muted {
    font-size: 12px;
    color: #9ca3af;
}

QLabel.stat-value {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
}

/* Primary Action Buttons */
QPushButton.btn-primary {
    background-color: #6366f1;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton.btn-primary:hover {
    background-color: #4f46e5;
}

QPushButton.btn-primary:pressed {
    background-color: #4338ca;
}

QPushButton.btn-primary:disabled {
    background-color: #373844;
    color: #6b7280;
}

/* Secondary Buttons */
QPushButton.btn-secondary {
    background-color: #282a35;
    color: #e5e7eb;
    border: 1px solid #3b3e4f;
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton.btn-secondary:hover {
    background-color: #323543;
    border-color: #4f5266;
}

QPushButton.btn-secondary:pressed {
    background-color: #242630;
}

/* Dedicated Table Copy Button */
QPushButton.btn-copy {
    background-color: #282a35;
    color: #e5e7eb;
    border: 1px solid #3b3e4f;
    border-radius: 6px;
    padding: 0px 4px;
    font-size: 12px;
    font-weight: 600;
    text-align: center;
}

QPushButton.btn-copy:hover {
    background-color: #323543;
    border-color: #6366f1;
    color: #ffffff;
}

QPushButton.btn-copy:pressed {
    background-color: #20222a;
}

/* Danger / Stop Button */
QPushButton.btn-danger {
    background-color: #ef4444;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton.btn-danger:hover {
    background-color: #dc2626;
}

/* Progress Bars */
QProgressBar {
    background-color: #23252d;
    border: none;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #a855f7);
    border-radius: 6px;
}

/* Tables */
QTableWidget {
    background-color: #18191e;
    border: 1px solid #282a35;
    border-radius: 10px;
    gridline-color: #23252d;
    outline: none;
}

QTableWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #21232a;
}

QTableWidget::item:selected {
    background-color: #2e303d;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #1e2027;
    color: #9ca3af;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #282a35;
}

/* Inputs, TextEdits, ComboBoxes, SpinBoxes */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #1a1c22;
    border: 1px solid #2f3240;
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
    font-size: 13px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #6366f1;
}

QComboBox {
    background-color: #1a1c22;
    border: 1px solid #2f3240;
    border-radius: 8px;
    padding: 8px 14px;
    color: #ffffff;
    font-weight: 500;
}

QComboBox:hover {
    border-color: #3f4357;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #20222a;
    border: 1px solid #323543;
    border-radius: 8px;
    selection-background-color: #2e303d;
    selection-color: #ffffff;
    outline: none;
}

QSpinBox {
    background-color: #1a1c22;
    border: 1px solid #2f3240;
    border-radius: 8px;
    padding: 6px 10px;
    color: #ffffff;
    min-width: 70px;
}

QCheckBox {
    color: #e5e7eb;
    font-weight: 500;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #3b3e4f;
    background-color: #1a1c22;
}

QCheckBox::indicator:checked {
    background-color: #6366f1;
    border-color: #6366f1;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #282a35;
    background-color: #1a1c22;
    border-radius: 10px;
    padding: 12px;
}

QTabBar::tab {
    background-color: #18191e;
    color: #9ca3af;
    padding: 8px 16px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #1a1c22;
    color: #818cf8;
    border-bottom: 2px solid #6366f1;
}

QTabBar::tab:hover:!selected {
    background-color: #23252d;
    color: #e5e7eb;
}

/* Active testing banner */
#activeBanner {
    background-color: #1a1d26;
    border: 1px solid #2b2f3e;
    border-radius: 8px;
    padding: 6px 12px;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #2f3240;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4b4f63;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #2f3240;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4b4f63;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""

LIGHT_STYLESHEET = """
/* Global Reset */
QWidget {
    background-color: #f8fafc;
    color: #0f172a;
    font-family: "Segoe UI Variable Text", "Segoe UI", -apple-system, sans-serif;
    font-size: 13px;
    selection-background-color: #4f46e5;
    selection-color: #ffffff;
}

/* Main Window */
QMainWindow {
    background-color: #f8fafc;
}

/* Sidebar Navigation */
#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e2e8f0;
    min-width: 210px;
    max-width: 210px;
}

#sidebarTitle {
    font-size: 19px;
    font-weight: 800;
    color: #0f172a;
    padding: 18px 16px 14px 16px;
    letter-spacing: -0.5px;
}

/* Navigation Buttons */
QPushButton.nav-btn {
    background-color: transparent;
    color: #475569;
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    margin: 2px 8px;
}

QPushButton.nav-btn:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}

QPushButton.nav-btn:checked {
    background-color: #e0e7ff;
    color: #4338ca;
    font-weight: 600;
    border-left: 3px solid #4f46e5;
}

/* Card Containers */
QFrame.card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}

QFrame.card-highlight {
    background-color: #ffffff;
    border: 1px solid #c7d2fe;
    border-radius: 12px;
}

/* Headers & Labels */
QLabel.heading-1 {
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
}

QLabel.heading-2 {
    font-size: 15px;
    font-weight: 600;
    color: #1e293b;
}

QLabel.label-muted {
    font-size: 12px;
    color: #64748b;
}

QLabel.stat-value {
    font-size: 26px;
    font-weight: 800;
    color: #0f172a;
}

/* Primary Action Buttons */
QPushButton.btn-primary {
    background-color: #4f46e5;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton.btn-primary:hover {
    background-color: #4338ca;
}

QPushButton.btn-primary:pressed {
    background-color: #3730a3;
}

QPushButton.btn-primary:disabled {
    background-color: #e2e8f0;
    color: #94a3b8;
}

/* Secondary Buttons */
QPushButton.btn-secondary {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton.btn-secondary:hover {
    background-color: #f1f5f9;
    border-color: #94a3b8;
}

QPushButton.btn-secondary:pressed {
    background-color: #e2e8f0;
}

/* Dedicated Table Copy Button */
QPushButton.btn-copy {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 0px 4px;
    font-size: 12px;
    font-weight: 600;
    text-align: center;
}

QPushButton.btn-copy:hover {
    background-color: #f1f5f9;
    border-color: #4f46e5;
    color: #0f172a;
}

QPushButton.btn-copy:pressed {
    background-color: #e2e8f0;
}

/* Danger / Stop Button */
QPushButton.btn-danger {
    background-color: #ef4444;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton.btn-danger:hover {
    background-color: #dc2626;
}

/* Progress Bars */
QProgressBar {
    background-color: #e2e8f0;
    border: none;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #8b5cf6);
    border-radius: 6px;
}

/* Tables */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    gridline-color: #f1f5f9;
    outline: none;
}

QTableWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #f1f5f9;
    color: #1e293b;
}

QTableWidget::item:selected {
    background-color: #e0e7ff;
    color: #1e1b4b;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #64748b;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #e2e8f0;
}

/* Inputs, TextEdits, ComboBoxes, SpinBoxes */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 12px;
    color: #0f172a;
    font-size: 13px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #4f46e5;
}

QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 14px;
    color: #0f172a;
    font-weight: 500;
}

QComboBox:hover {
    border-color: #94a3b8;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    selection-background-color: #e0e7ff;
    selection-color: #1e1b4b;
    outline: none;
}

QSpinBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px 10px;
    color: #0f172a;
    min-width: 70px;
}

QCheckBox {
    color: #1e293b;
    font-weight: 500;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #cbd5e1;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #4f46e5;
    border-color: #4f46e5;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    background-color: #ffffff;
    border-radius: 10px;
    padding: 12px;
}

QTabBar::tab {
    background-color: #f1f5f9;
    color: #64748b;
    padding: 8px 16px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #4f46e5;
    border-bottom: 2px solid #4f46e5;
}

QTabBar::tab:hover:!selected {
    background-color: #e2e8f0;
    color: #0f172a;
}

/* Active testing banner */
#activeBanner {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 6px 12px;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #cbd5e1;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #94a3b8;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""


def get_stylesheet(theme: str = "dark") -> str:
    """Return QSS stylesheet for requested theme ('dark' or 'light')."""
    return LIGHT_STYLESHEET if theme.lower() == "light" else DARK_STYLESHEET
