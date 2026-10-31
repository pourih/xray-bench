"""Modern dark and light theme styling and QSS stylesheets for xBench GUI."""
from pathlib import Path

_ASSETS_DIR = Path(__file__).resolve().parents[3] / "assets"
_CHECK_ICON = str((_ASSETS_DIR / "check.svg")).replace("\\", "/")
_CHEVRON_DARK = str((_ASSETS_DIR / "chevron-down-dark.svg")).replace("\\", "/")
_CHEVRON_LIGHT = str((_ASSETS_DIR / "chevron-down-light.svg")).replace("\\", "/")
_SPIN_UP_DARK = str((_ASSETS_DIR / "spin-up-dark.svg")).replace("\\", "/")
_SPIN_DOWN_DARK = str((_ASSETS_DIR / "spin-down-dark.svg")).replace("\\", "/")
_SPIN_UP_LIGHT = str((_ASSETS_DIR / "spin-up-light.svg")).replace("\\", "/")
_SPIN_DOWN_LIGHT = str((_ASSETS_DIR / "spin-down-light.svg")).replace("\\", "/")

_RAW_DARK_STYLESHEET = """
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
    font-size: 24px;
    font-weight: 800;
    color: #ffffff;
    background-color: transparent;
    padding: 0px;
    letter-spacing: -0.5px;
    qproperty-alignment: AlignCenter;
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
QLabel {
    background-color: transparent;
}

QLabel.heading-1 {
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
    background-color: transparent;
}

QLabel.heading-2 {
    font-size: 15px;
    font-weight: 600;
    color: #e5e7eb;
    background-color: transparent;
}

QLabel.label-muted {
    font-size: 12px;
    color: #9ca3af;
    background-color: transparent;
}

QLabel.stat-value {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
    background-color: transparent;
}

/* Card & Banner Child Transparencies */
QFrame.card QLabel,
QFrame.card-highlight QLabel,
#statCard QLabel,
#activeBanner QLabel {
    background-color: transparent;
}

QFrame.card QCheckBox,
QFrame.card-highlight QCheckBox {
    background-color: transparent;
}

/* Badge Pills */
#statusPill {
    background-color: #282a35;
    color: #9ca3af;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
}

#statusPill[running="true"] {
    background-color: #312e81;
    color: #a5b4fc;
}

#streamCounter {
    background-color: #23252d;
    color: #9ca3af;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
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

QPushButton.btn-danger:disabled {
    background-color: #2b1f22;
    color: #7f555c;
    border: 1px solid #3d282d;
}

/* Progress Bars */
QProgressBar {
    background-color: #16181f;
    border: 1px solid #232530;
    border-radius: 6px;
    height: 8px;
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

QHeaderView {
    background-color: #1e2027;
    border: none;
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

QTableCornerButton::section {
    background-color: #1e2027;
    border: none;
}

/* Inputs, TextEdits, ComboBoxes, SpinBoxes */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #1a1c22;
    border: 1px solid #3b3e4f;
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
    font-size: 13px;
}

QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {
    border-color: #4f5266;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #6366f1;
}

QComboBox {
    background-color: #1a1c22;
    border: 1px solid #3b3e4f;
    border-radius: 8px;
    padding: 8px 32px 8px 14px;
    color: #ffffff;
    font-weight: 500;
}

QComboBox:hover {
    border-color: #4f5266;
}

QComboBox:focus {
    border: 1px solid #6366f1;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: none;
    background: transparent;
}

QComboBox::down-arrow {
    image: url("__CHEVRON_DARK__");
    width: 12px;
    height: 12px;
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
    border: 1px solid #3b3e4f;
    border-radius: 8px;
    padding: 6px 26px 6px 10px;
    color: #ffffff;
    min-width: 70px;
}

QSpinBox:hover {
    border-color: #4f5266;
}

QSpinBox:focus {
    border: 1px solid #6366f1;
}

QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #2f3240;
    border-bottom: 1px solid #2f3240;
    border-top-right-radius: 8px;
    background-color: #23252d;
}

QSpinBox::up-button:hover {
    background-color: #2e303d;
}

QSpinBox::up-arrow {
    image: url("__SPIN_UP_DARK__");
    width: 8px;
    height: 8px;
}

QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    border-left: 1px solid #2f3240;
    border-bottom-right-radius: 8px;
    background-color: #23252d;
}

QSpinBox::down-button:hover {
    background-color: #2e303d;
}

QSpinBox::down-arrow {
    image: url("__SPIN_DOWN_DARK__");
    width: 8px;
    height: 8px;
}

QCheckBox {
    background-color: transparent;
    color: #e5e7eb;
    font-weight: 500;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #4b4f63;
    background-color: #1a1c22;
}

QCheckBox::indicator:hover {
    border-color: #6366f1;
}

QCheckBox::indicator:checked {
    background-color: #6366f1;
    border-color: #6366f1;
    image: url("__CHECK_ICON__");
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

/* ScrollArea Containers */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #121316;
    width: 8px;
    margin: 0px;
    border: none;
}

QScrollBar::track:vertical {
    background-color: #18191e;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #2b2e3b;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3f4357;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
    border: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    background-color: #121316;
    height: 8px;
    margin: 0px;
    border: none;
}

QScrollBar::track:horizontal {
    background-color: #18191e;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #2b2e3b;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #3f4357;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    background: none;
    border: none;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}
"""

_RAW_LIGHT_STYLESHEET = """
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
    font-size: 24px;
    font-weight: 800;
    color: #0f172a;
    background-color: transparent;
    padding: 0px;
    letter-spacing: -0.5px;
    qproperty-alignment: AlignCenter;
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
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}

/* Headers & Labels */
QLabel {
    background-color: transparent;
}

QLabel.heading-1 {
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
    background-color: transparent;
}

QLabel.heading-2 {
    font-size: 15px;
    font-weight: 600;
    color: #1e293b;
    background-color: transparent;
}

QLabel.label-muted {
    font-size: 12px;
    color: #64748b;
    background-color: transparent;
}

QLabel.stat-value {
    font-size: 26px;
    font-weight: 800;
    color: #0f172a;
    background-color: transparent;
}

/* Card & Banner Child Transparencies */
QFrame.card QLabel,
QFrame.card-highlight QLabel,
#statCard QLabel,
#activeBanner QLabel {
    background-color: transparent;
}

QFrame.card QCheckBox,
QFrame.card-highlight QCheckBox {
    background-color: transparent;
}

/* Badge Pills */
#statusPill {
    background-color: #e2e8f0;
    color: #475569;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
}

#statusPill[running="true"] {
    background-color: #e0e7ff;
    color: #4338ca;
}

#streamCounter {
    background-color: #f1f5f9;
    color: #64748b;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
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

QPushButton.btn-danger:disabled {
    background-color: #fee2e2;
    color: #fca5a5;
    border: 1px solid #fecaca;
}

/* Progress Bars */
QProgressBar {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    height: 8px;
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

QHeaderView {
    background-color: #f8fafc;
    border: none;
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

QTableCornerButton::section {
    background-color: #f8fafc;
    border: none;
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

QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {
    border-color: #94a3b8;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #4f46e5;
}

QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 32px 8px 14px;
    color: #0f172a;
    font-weight: 500;
}

QComboBox:hover {
    border-color: #94a3b8;
}

QComboBox:focus {
    border: 1px solid #4f46e5;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: none;
    background: transparent;
}

QComboBox::down-arrow {
    image: url("__CHEVRON_LIGHT__");
    width: 12px;
    height: 12px;
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
    padding: 6px 26px 6px 10px;
    color: #0f172a;
    min-width: 70px;
}

QSpinBox:hover {
    border-color: #94a3b8;
}

QSpinBox:focus {
    border: 1px solid #4f46e5;
}

QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
    border-top-right-radius: 8px;
    background-color: #f8fafc;
}

QSpinBox::up-button:hover {
    background-color: #f1f5f9;
}

QSpinBox::up-arrow {
    image: url("__SPIN_UP_LIGHT__");
    width: 8px;
    height: 8px;
}

QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    border-left: 1px solid #e2e8f0;
    border-bottom-right-radius: 8px;
    background-color: #f8fafc;
}

QSpinBox::down-button:hover {
    background-color: #f1f5f9;
}

QSpinBox::down-arrow {
    image: url("__SPIN_DOWN_LIGHT__");
    width: 8px;
    height: 8px;
}

QCheckBox {
    background-color: transparent;
    color: #1e293b;
    font-weight: 500;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #94a3b8;
    background-color: #ffffff;
}

QCheckBox::indicator:hover {
    border-color: #4f46e5;
}

QCheckBox::indicator:checked {
    background-color: #4f46e5;
    border-color: #4f46e5;
    image: url("__CHECK_ICON__");
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

/* ScrollArea Containers */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
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

DARK_STYLESHEET = _RAW_DARK_STYLESHEET \
    .replace("__CHECK_ICON__", _CHECK_ICON) \
    .replace("__CHEVRON_DARK__", _CHEVRON_DARK) \
    .replace("__SPIN_UP_DARK__", _SPIN_UP_DARK) \
    .replace("__SPIN_DOWN_DARK__", _SPIN_DOWN_DARK)

LIGHT_STYLESHEET = _RAW_LIGHT_STYLESHEET \
    .replace("__CHECK_ICON__", _CHECK_ICON) \
    .replace("__CHEVRON_LIGHT__", _CHEVRON_LIGHT) \
    .replace("__SPIN_UP_LIGHT__", _SPIN_UP_LIGHT) \
    .replace("__SPIN_DOWN_LIGHT__", _SPIN_DOWN_LIGHT)


def get_stylesheet(theme: str = "dark") -> str:
    """Return QSS stylesheet for requested theme ('dark' or 'light')."""
    return LIGHT_STYLESHEET if theme.lower() == "light" else DARK_STYLESHEET
