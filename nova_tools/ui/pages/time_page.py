"""Zaman araçları: kronometre, geri sayım, Pomodoro, dünya saatleri."""
from __future__ import annotations

import json

from PySide6.QtCore import QElapsedTimer, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QComboBox, QGridLayout, QHBoxLayout, QLabel, QListWidget, QPushButton,
    QSpinBox, QSystemTrayIcon, QTabWidget, QVBoxLayout, QWidget,
)

from ...core import timeutil as TU
from ..widgets import Card, RingProgress, muted_label, page_header, primary_button


def alert(main, title: str, text: str) -> None:
    """Süre dolduğunda sesli uyarı + durum çubuğu + (varsa) sistem bildirimi."""
    QApplication.beep()
    main.notify(f"⏰ {title}: {text}", 10000)
    tray = getattr(main, "_tray", None)
    if tray is None and QSystemTrayIcon.isSystemTrayAvailable():
        tray = QSystemTrayIcon(main.windowIcon(), main)
        tray.show()
        main._tray = tray
    if tray is not None:
        tray.showMessage(title, text, QSystemTrayIcon.Information, 8000)
    QApplication.alert(main, 0)


class StopwatchTab(QWidget):
    def __init__(self):
        super().__init__()
        self.elapsed = QElapsedTimer()
        self.accum = 0
        self.running = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 0)
        self.display = QLabel(TU.format_duration(0))
        self.display.setObjectName("ClockBig")
        self.display.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.display)
        row = QHBoxLayout()
        row.addStretch(1)
        self.start_btn = primary_button("Başlat")
        self.lap_btn = QPushButton("Tur")
        self.reset_btn = QPushButton("Sıfırla")
        self.start_btn.clicked.connect(self.toggle)
        self.lap_btn.clicked.connect(self.lap)
        self.reset_btn.clicked.connect(self.reset)
        for b in (self.start_btn, self.lap_btn, self.reset_btn):
            b.setMinimumWidth(110)
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.laps = QListWidget()
        lay.addWidget(self.laps, 1)
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.refresh)
        self._last_lap = 0

    def current_ms(self) -> int:
        return self.accum + (self.elapsed.elapsed() if self.running else 0)

    def toggle(self) -> None:
        if self.running:
            self.accum += self.elapsed.elapsed()
            self.running = False
            self.timer.stop()
            self.start_btn.setText("Devam")
        else:
            self.elapsed.start()
            self.running = True
            self.timer.start()
            self.start_btn.setText("Duraklat")
        self.refresh()

    def lap(self) -> None:
        now = self.current_ms()
        if now == 0:
            return
        n = self.laps.count() + 1
        self.laps.insertItem(0, f"Tur {n}:  {TU.format_duration(now - self._last_lap)}   (toplam {TU.format_duration(now)})")
        self._last_lap = now

    def reset(self) -> None:
        self.running = False
        self.timer.stop()
        self.accum = 0
        self._last_lap = 0
        self.laps.clear()
        self.start_btn.setText("Başlat")
        self.refresh()

    def refresh(self) -> None:
        self.display.setText(TU.format_duration(self.current_ms()))


class CountdownTab(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.total = 0
        self.remaining = 0
        self.running = False
        self.clock = QElapsedTimer()
        self.base_remaining = 0
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 0)
        self.ring = RingProgress()
        lay.addWidget(self.ring, 3)
        side = Card("Süre")
        grid = QGridLayout()
        self.h, self.m, self.s = QSpinBox(), QSpinBox(), QSpinBox()
        self.h.setRange(0, 99)
        self.m.setRange(0, 59)
        self.s.setRange(0, 59)
        self.m.setValue(5)
        for i, (lbl, sp) in enumerate((("Saat", self.h), ("Dakika", self.m), ("Saniye", self.s))):
            grid.addWidget(muted_label(lbl), 0, i)
            grid.addWidget(sp, 1, i)
        side.body.addLayout(grid)
        presets = QHBoxLayout()
        for mins in (1, 5, 10, 15, 30):
            b = QPushButton(f"{mins} dk")
            b.clicked.connect(lambda _=False, m=mins: self._preset(m))
            presets.addWidget(b)
        side.body.addLayout(presets)
        self.start_btn = primary_button("Başlat")
        self.reset_btn = QPushButton("Sıfırla")
        self.start_btn.clicked.connect(self.toggle)
        self.reset_btn.clicked.connect(self.reset)
        side.body.addWidget(self.start_btn)
        side.body.addWidget(self.reset_btn)
        side.body.addStretch(1)
        lay.addWidget(side, 2)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._tick)
        self.reset()

    def _preset(self, mins: int) -> None:
        self.h.setValue(mins // 60)
        self.m.setValue(mins % 60)
        self.s.setValue(0)
        self.reset()

    def _set_inputs_enabled(self, on: bool) -> None:
        for w in (self.h, self.m, self.s):
            w.setEnabled(on)

    def toggle(self) -> None:
        if self.running:
            self._tick()
            self.running = False
            self.timer.stop()
            self.start_btn.setText("Devam")
            return
        if self.remaining <= 0:
            self.reset()
        if self.total <= 0:
            self.main.notify("Önce bir süre girin.")
            return
        self.base_remaining = self.remaining
        self.clock.start()
        self.running = True
        self.timer.start()
        self.start_btn.setText("Duraklat")
        self._set_inputs_enabled(False)

    def reset(self) -> None:
        self.running = False
        self.timer.stop()
        self.total = (self.h.value() * 3600 + self.m.value() * 60 + self.s.value()) * 1000
        self.remaining = self.total
        self.start_btn.setText("Başlat")
        self._set_inputs_enabled(True)
        self._paint()

    def _tick(self) -> None:
        if self.running:
            self.remaining = max(0, self.base_remaining - self.clock.elapsed())
        self._paint()
        if self.running and self.remaining <= 0:
            self.running = False
            self.timer.stop()
            self.start_btn.setText("Başlat")
            self._set_inputs_enabled(True)
            alert(self.main, "Geri sayım bitti", "Belirlediğiniz süre doldu.")

    def _paint(self) -> None:
        frac = (self.remaining / self.total) if self.total else 0
        secs = (self.remaining + 999) // 1000
        self.ring.set_state(frac, TU.format_duration(secs * 1000, show_centis=False),
                            "Çalışıyor" if self.running else ("Bitti" if self.total and not self.remaining else "Hazır"))


class PomodoroTab(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.cycle = TU.PomodoroCycle()
        self.running = False
        self.clock = QElapsedTimer()
        self.base = 0
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 0)
        self.ring = RingProgress()
        lay.addWidget(self.ring, 3)
        side = Card("Pomodoro")
        grid = QGridLayout()
        self.work, self.short, self.long, self.rounds = QSpinBox(), QSpinBox(), QSpinBox(), QSpinBox()
        for sp, rng, val in ((self.work, (1, 180), 25), (self.short, (1, 60), 5),
                             (self.long, (1, 120), 15), (self.rounds, (1, 12), 4)):
            sp.setRange(*rng)
            sp.setValue(val)
            sp.valueChanged.connect(self._config_changed)
        for i, (lbl, sp) in enumerate((("Odak (dk)", self.work), ("Kısa mola (dk)", self.short),
                                       ("Uzun mola (dk)", self.long), ("Uzun mola için tur", self.rounds))):
            grid.addWidget(muted_label(lbl), i, 0)
            grid.addWidget(sp, i, 1)
        side.body.addLayout(grid)
        self.phase_lbl = QLabel()
        self.phase_lbl.setObjectName("CardTitle")
        self.count_lbl = muted_label()
        side.body.addWidget(self.phase_lbl)
        side.body.addWidget(self.count_lbl)
        self.start_btn = primary_button("Başlat")
        self.skip_btn = QPushButton("Sonraki aşama")
        self.reset_btn = QPushButton("Sıfırla")
        self.start_btn.clicked.connect(self.toggle)
        self.skip_btn.clicked.connect(self.skip)
        self.reset_btn.clicked.connect(self.reset)
        for b in (self.start_btn, self.skip_btn, self.reset_btn):
            side.body.addWidget(b)
        side.body.addStretch(1)
        lay.addWidget(side, 2)
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self._tick)
        self._config_changed()

    def _config_changed(self) -> None:
        self.cycle.config = TU.PomodoroConfig(self.work.value(), self.short.value(),
                                              self.long.value(), self.rounds.value())
        if not self.running:
            self.remaining = self.cycle.duration_ms()
            self._paint()

    def toggle(self) -> None:
        if self.running:
            self._tick()
            self.running = False
            self.timer.stop()
            self.start_btn.setText("Devam")
        else:
            self.base = self.remaining
            self.clock.start()
            self.running = True
            self.timer.start()
            self.start_btn.setText("Duraklat")
        self._paint()

    def skip(self) -> None:
        self.cycle.advance()
        self.remaining = self.cycle.duration_ms()
        if self.running:
            self.base = self.remaining
            self.clock.start()
        self._paint()

    def reset(self) -> None:
        self.running = False
        self.timer.stop()
        self.cycle.reset()
        self.remaining = self.cycle.duration_ms()
        self.start_btn.setText("Başlat")
        self._paint()

    def _tick(self) -> None:
        if self.running:
            self.remaining = max(0, self.base - self.clock.elapsed())
            if self.remaining <= 0:
                finished = TU.PHASE_NAMES[self.cycle.phase]
                nxt = self.cycle.advance()
                self.remaining = self.cycle.duration_ms()
                self.base = self.remaining
                self.clock.start()
                alert(self.main, f"{finished} bitti", f"Sıradaki: {TU.PHASE_NAMES[nxt]}")
        self._paint()

    def _paint(self) -> None:
        total = self.cycle.duration_ms()
        secs = (self.remaining + 999) // 1000
        self.ring.set_state(self.remaining / total if total else 0,
                            TU.format_duration(secs * 1000, show_centis=False)[3:] if secs < 3600
                            else TU.format_duration(secs * 1000, show_centis=False),
                            TU.PHASE_NAMES[self.cycle.phase])
        self.phase_lbl.setText(f"Aşama: {TU.PHASE_NAMES[self.cycle.phase]}")
        self.count_lbl.setText(f"Tamamlanan odak: {self.cycle.completed_work}  •  "
                               f"Tur {self.cycle.round_in_set}/{self.cycle.config.rounds_before_long}")


class WorldClockTab(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 0)
        row = QHBoxLayout()
        self.combo = QComboBox()
        for label, tz in TU.COMMON_ZONES:
            self.combo.addItem(f"{label} ({tz})", tz)
        add = primary_button("Ekle")
        add.clicked.connect(self.add_clock)
        remove = QPushButton("Seçiliyi kaldır")
        remove.clicked.connect(self.remove_selected)
        row.addWidget(self.combo, 1)
        row.addWidget(add)
        row.addWidget(remove)
        lay.addLayout(row)
        self.grid = QGridLayout()
        self.grid.setSpacing(12)
        lay.addLayout(self.grid)
        lay.addStretch(1)
        self.cards: list[tuple[str, Card, QLabel, QLabel]] = []
        self.selected: str | None = None
        try:
            zones = json.loads(main.storage.get("world_clocks", "")) or TU.DEFAULT_CLOCKS
        except (ValueError, TypeError):
            zones = TU.DEFAULT_CLOCKS
        self.zones: list[str] = []
        for z in zones:
            self._add(z, save=False)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def _add(self, tz: str, save: bool = True) -> None:
        if tz in self.zones:
            self.main.notify("Bu saat zaten listede.")
            return
        try:
            TU.world_time(tz)
        except (ValueError, RuntimeError) as e:
            self.main.notify(str(e))
            return
        self.zones.append(tz)
        card = Card()
        card.setCursor(Qt.PointingHandCursor)
        name = QLabel(TU.zone_label(tz))
        name.setObjectName("CardTitle")
        clock = QLabel("--:--:--")
        clock.setObjectName("BigValue")
        meta = muted_label()
        card.body.addWidget(name)
        card.body.addWidget(clock)
        card.body.addWidget(meta)
        card.mousePressEvent = lambda _e, z=tz: self._select(z)
        self.cards.append((tz, card, clock, meta))
        self._relayout()
        if save:
            self._save()
        self.refresh()

    def _select(self, tz: str) -> None:
        self.selected = tz
        for z, card, _c, _m in self.cards:
            card.setStyleSheet("QFrame#Card { border: 1px solid #8B5CF6; }" if z == tz else "")

    def _relayout(self) -> None:
        for _z, card, _c, _m in self.cards:
            self.grid.removeWidget(card)
        for i, (_z, card, _c, _m) in enumerate(self.cards):
            self.grid.addWidget(card, i // 3, i % 3)

    def add_clock(self) -> None:
        self._add(self.combo.currentData())

    def remove_selected(self) -> None:
        if not self.selected:
            self.main.notify("Kaldırmak için önce bir saat kartına tıklayın.")
            return
        for i, (z, card, _c, _m) in enumerate(self.cards):
            if z == self.selected:
                self.grid.removeWidget(card)
                card.deleteLater()
                self.cards.pop(i)
                self.zones.remove(z)
                break
        self.selected = None
        self._relayout()
        self._save()

    def _save(self) -> None:
        self.main.storage.set("world_clocks", json.dumps(self.zones))

    def refresh(self) -> None:
        days = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        for tz, _card, clock, meta in self.cards:
            try:
                t = TU.world_time(tz)
            except (ValueError, RuntimeError):
                continue
            clock.setText(t.strftime("%H:%M:%S"))
            meta.setText(f"{days[t.weekday()]} {t.strftime('%d.%m.%Y')}  •  {TU.utc_offset_text(t)}")


class TimePage(QWidget):
    def __init__(self, main):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.addWidget(page_header("Zaman Araçları", "Kronometre, geri sayım, Pomodoro ve dünya saatleri."))
        self.tabs = QTabWidget()
        self.stopwatch = StopwatchTab()
        self.countdown = CountdownTab(main)
        self.pomodoro = PomodoroTab(main)
        self.clocks = WorldClockTab(main)
        self.tabs.addTab(self.stopwatch, "Kronometre")
        self.tabs.addTab(self.countdown, "Geri Sayım")
        self.tabs.addTab(self.pomodoro, "Pomodoro")
        self.tabs.addTab(self.clocks, "Dünya Saatleri")
        lay.addWidget(self.tabs, 1)

    def open_tab(self, index: int) -> None:
        self.tabs.setCurrentIndex(index)
