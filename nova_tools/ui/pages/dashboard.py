"""Ana sayfa: hızlı erişim kartları ve son kullanılan araçlar."""
from __future__ import annotations

import time
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget,
)

from ..widgets import Card, muted_label, scroll_page

# (başlık, açıklama, simge, sayfa, sekme)
QUICK_TOOLS = [
    ("Dosya Arama", "Ada, uzantıya ve boyuta göre bul", "🔎", "files", 0),
    ("Yinelenen Dosyalar", "Aynı içerikli dosyaları tespit et", "🧬", "files", 1),
    ("Klasör Analizi", "Boyut dağılımı ve en büyük dosyalar", "📊", "files", 2),
    ("Metin Editörü", "Aç, düzenle, kaydet", "✍️", "text", 0),
    ("Kelime Sayacı", "Kelime, karakter, cümle", "🔤", "text", 1),
    ("JSON Biçimlendir", "Doğrula, güzelleştir, küçült", "🧾", "text", 3),
    ("Hesap Makinesi", "Bilimsel hesaplamalar", "🧮", "calc", 0),
    ("Birim Dönüştürücü", "Uzunluk, ağırlık, sıcaklık…", "📐", "calc", 1),
    ("SHA-256", "Metin ve dosya özeti", "🔐", "calc", 2),
    ("Pomodoro", "Odaklanma zamanlayıcısı", "🍅", "time", 2),
    ("Dünya Saatleri", "Farklı şehirlerde saat", "🌍", "time", 3),
    ("Hızlı Notlar", "Otomatik kaydedilen notlar", "🗒️", "notes", None),
]


class ToolCard(QFrame):
    def __init__(self, title: str, desc: str, icon: str, on_click):
        super().__init__()
        self.setObjectName("ToolCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(92)
        self._on_click = on_click
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        ic = QLabel(icon)
        ic.setObjectName("CardIcon")
        ic.setFixedWidth(44)
        lay.addWidget(ic)
        col = QVBoxLayout()
        t = QLabel(title)
        t.setObjectName("CardTitle")
        d = muted_label(desc)
        col.addWidget(t)
        col.addWidget(d)
        lay.addLayout(col, 1)
        self.setToolTip(f"{title} aracını aç")

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self._on_click()
        super().mouseReleaseEvent(event)


class DashboardPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        self.greet = QLabel()
        self.greet.setObjectName("PageTitle")
        self.date = muted_label()
        lay.addWidget(self.greet)
        lay.addWidget(self.date)

        # Özet kartları
        stats = QHBoxLayout()
        self.stat_notes = self._stat_card(stats, "Notlar", "🗒️")
        self.stat_recent = self._stat_card(stats, "Son kullanılan", "🕘")
        self.stat_clock = self._stat_card(stats, "Saat", "⏰")
        lay.addLayout(stats)

        title = QLabel("Hızlı erişim")
        title.setObjectName("CardTitle")
        lay.addWidget(title)
        self.grid = QGridLayout()
        self.grid.setSpacing(12)
        self.cards: list[ToolCard] = []
        for (t, d, ic, key, tab) in QUICK_TOOLS:
            card = ToolCard(t, d, ic, lambda k=key, tb=tab: self.main.navigate(k, tb))
            self.cards.append(card)
        lay.addLayout(self.grid)
        self._columns = 0

        recent_card = Card("Son kullanılan araçlar")
        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(200)
        self.recent_list.itemActivated.connect(self._open_recent)
        self.recent_list.itemClicked.connect(self._open_recent)
        recent_card.body.addWidget(self.recent_list)
        lay.addWidget(recent_card)
        lay.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll_page(content))

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._relayout()
        self.on_show()

    def _stat_card(self, parent_layout, label: str, icon: str) -> QLabel:
        card = Card()
        row = QHBoxLayout()
        ic = QLabel(icon)
        ic.setObjectName("CardIcon")
        row.addWidget(ic)
        col = QVBoxLayout()
        value = QLabel("–")
        value.setObjectName("BigValue")
        col.addWidget(value)
        col.addWidget(muted_label(label))
        row.addLayout(col, 1)
        card.body.addLayout(row)
        parent_layout.addWidget(card, 1)
        return value

    def _relayout(self) -> None:
        cols = 3 if self.width() >= 900 else 2
        if cols == self._columns:
            return
        self._columns = cols
        for c in self.cards:
            self.grid.removeWidget(c)
        for i, c in enumerate(self.cards):
            self.grid.addWidget(c, i // cols, i % cols)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()

    def _tick(self) -> None:
        now = datetime.now()
        self.stat_clock.setText(now.strftime("%H:%M:%S"))
        h = now.hour
        greet = "Günaydın" if 5 <= h < 12 else "İyi günler" if 12 <= h < 18 else "İyi akşamlar"
        self.greet.setText(f"{greet} 👋")
        days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
                  "Eylül", "Ekim", "Kasım", "Aralık"]
        self.date.setText(f"{now.day} {months[now.month - 1]} {now.year}, {days[now.weekday()]}")

    def on_show(self) -> None:
        from ..main_window import TOOL_LABELS
        self._tick()
        self.stat_notes.setText(str(self.main.storage.note_count()))
        recent = self.main.storage.recent_tools()
        self.stat_recent.setText(TOOL_LABELS.get(recent[0][0], "–") if recent else "–")
        self.recent_list.clear()
        if not recent:
            item = QListWidgetItem("Henüz araç kullanılmadı. Yukarıdaki kartlardan birini seçin.")
            item.setFlags(Qt.NoItemFlags)
            self.recent_list.addItem(item)
        for key, used_at, count in recent:
            ago = _ago(time.time() - used_at)
            item = QListWidgetItem(f"{TOOL_LABELS.get(key, key)}   •   {ago}   •   {count} kez")
            item.setData(Qt.UserRole, key)
            self.recent_list.addItem(item)

    def _open_recent(self, item: QListWidgetItem) -> None:
        key = item.data(Qt.UserRole)
        if key:
            self.main.navigate(key)


def _ago(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return "az önce"
    if s < 3600:
        return f"{s // 60} dk önce"
    if s < 86400:
        return f"{s // 3600} sa önce"
    return f"{s // 86400} gün önce"
