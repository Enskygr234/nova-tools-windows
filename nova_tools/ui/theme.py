"""Koyu ve açık tema için Qt stil sayfası (mor/mavi vurgu)."""
from __future__ import annotations

PURPLE = "#8B5CF6"
BLUE = "#3B82F6"

PALETTES = {
    "dark": {
        "bg": "#0D0D18", "sidebar": "#11111E", "card": "#171728", "card2": "#1E1E33",
        "border": "#2A2A42", "text": "#E8E8F2", "muted": "#9A9AB6", "input": "#13131F",
        "hover": "#22223A", "sel": "#2D1F5C", "success": "#34D399", "danger": "#F87171",
        "warning": "#FBBF24",
    },
    "light": {
        "bg": "#F5F4FB", "sidebar": "#FFFFFF", "card": "#FFFFFF", "card2": "#F1EFFA",
        "border": "#E1DEEF", "text": "#16162A", "muted": "#61617E", "input": "#FFFFFF",
        "hover": "#EEEAFB", "sel": "#E4DBFF", "success": "#059669", "danger": "#DC2626",
        "warning": "#D97706",
    },
}


def palette(mode: str) -> dict:
    return PALETTES.get(mode, PALETTES["dark"])


def build_qss(mode: str = "dark") -> str:
    p = palette(mode)
    return f"""
* {{
    font-family: "Segoe UI", "Inter", "Noto Sans", sans-serif;
    font-size: 10pt;
    color: {p['text']};
}}
QMainWindow, QWidget#Root, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {{
    background: {p['bg']};
}}
QWidget#Sidebar {{
    background: {p['sidebar']};
    border-right: 1px solid {p['border']};
}}
QLabel#Logo {{
    font-size: 15pt; font-weight: 700; padding: 6px 8px;
    color: {PURPLE};
}}
QLabel#LogoSub {{ color: {p['muted']}; font-size: 8.5pt; padding: 0 8px 10px 8px; }}
QPushButton#NavButton {{
    text-align: left; padding: 10px 14px; border: none; border-radius: 10px;
    background: transparent; color: {p['muted']}; font-size: 10.5pt;
}}
QPushButton#NavButton:hover {{ background: {p['hover']}; color: {p['text']}; }}
QPushButton#NavButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {PURPLE}, stop:1 {BLUE});
    color: white; font-weight: 600;
}}
QLabel#PageTitle {{ font-size: 20pt; font-weight: 700; }}
QLabel#PageSubtitle {{ color: {p['muted']}; font-size: 10pt; }}
QLabel#Muted {{ color: {p['muted']}; }}
QLabel#BigValue {{ font-size: 22pt; font-weight: 700; }}
QLabel#Display {{ font-size: 26pt; font-weight: 600; font-family: "Segoe UI", "Consolas", monospace; }}
QLabel#ClockBig {{ font-size: 38pt; font-weight: 700; font-family: "Consolas", "Segoe UI", monospace; }}
QLabel#Success {{ color: {p['success']}; font-weight: 600; }}
QLabel#Danger {{ color: {p['danger']}; font-weight: 600; }}
QFrame#Card {{
    background: {p['card']}; border: 1px solid {p['border']}; border-radius: 16px;
}}
QFrame#ToolCard {{
    background: {p['card']}; border: 1px solid {p['border']}; border-radius: 16px;
}}
QFrame#ToolCard:hover {{ border: 1px solid {PURPLE}; background: {p['card2']}; }}
QLabel#CardTitle {{ font-size: 11.5pt; font-weight: 600; }}
QLabel#CardIcon {{ font-size: 20pt; }}
QPushButton {{
    background: {p['card2']}; border: 1px solid {p['border']}; border-radius: 9px;
    padding: 7px 14px;
}}
QPushButton:hover {{ border-color: {PURPLE}; }}
QPushButton:pressed {{ background: {p['hover']}; }}
QPushButton:disabled {{ color: {p['muted']}; background: {p['card']}; }}
QPushButton#Primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {PURPLE}, stop:1 {BLUE});
    color: white; border: none; font-weight: 600;
}}
QPushButton#Primary:disabled {{ background: {p['border']}; color: {p['muted']}; }}
QPushButton#Danger {{ color: {p['danger']}; }}
QPushButton#CalcKey {{ font-size: 12pt; padding: 10px; min-height: 26px; }}
QPushButton#CalcOp {{ font-size: 12pt; padding: 10px; min-height: 26px; color: {PURPLE}; font-weight: 600; }}
QPushButton#CalcEq {{
    font-size: 13pt; padding: 10px; min-height: 26px; color: white; border: none; font-weight: 700;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {PURPLE}, stop:1 {BLUE});
}}
QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {p['input']}; border: 1px solid {p['border']}; border-radius: 9px;
    padding: 6px 8px; selection-background-color: {PURPLE}; selection-color: white;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QComboBox:focus {{ border: 1px solid {PURPLE}; }}
QComboBox QAbstractItemView {{
    background: {p['card']}; border: 1px solid {p['border']};
    selection-background-color: {p['sel']}; selection-color: {p['text']};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QTabWidget::pane {{ border: none; top: -1px; }}
QTabBar::tab {{
    background: transparent; color: {p['muted']}; padding: 8px 16px; margin-right: 4px;
    border-bottom: 2px solid transparent; font-weight: 600;
}}
QTabBar::tab:hover {{ color: {p['text']}; }}
QTabBar::tab:selected {{ color: {p['text']}; border-bottom: 2px solid {PURPLE}; }}
QTableWidget, QTreeWidget, QListWidget {{
    background: {p['card']}; border: 1px solid {p['border']}; border-radius: 12px;
    alternate-background-color: {p['card2']}; gridline-color: {p['border']};
}}
QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {{
    background: {p['sel']}; color: {p['text']};
}}
QListWidget::item {{ padding: 6px; border-radius: 8px; }}
QHeaderView::section {{
    background: {p['card2']}; color: {p['muted']}; border: none;
    border-bottom: 1px solid {p['border']}; padding: 6px; font-weight: 600;
}}
QProgressBar {{
    background: {p['card2']}; border: none; border-radius: 6px; height: 10px; text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    border-radius: 6px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {PURPLE}, stop:1 {BLUE});
}}
QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p['border']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {PURPLE}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {p['border']}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QToolTip {{ background: {p['card']}; color: {p['text']}; border: 1px solid {p['border']}; padding: 4px; }}
QStatusBar {{ background: {p['sidebar']}; color: {p['muted']}; border-top: 1px solid {p['border']}; }}
QMenu {{ background: {p['card']}; border: 1px solid {p['border']}; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; border-radius: 6px; }}
QMenu::item:selected {{ background: {p['sel']}; }}
QSplitter::handle {{ background: {p['border']}; }}
"""
