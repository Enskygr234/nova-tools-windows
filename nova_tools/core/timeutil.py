"""Zaman araçları için saf mantık: süre biçimleme, Pomodoro döngüsü, dünya saatleri."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore
    ZoneInfoNotFoundError = Exception  # type: ignore


def format_duration(ms: int, show_centis: bool = True) -> str:
    ms = max(0, int(ms))
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    base = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{base}.{millis // 10:02d}" if show_centis else base


@dataclass
class PomodoroConfig:
    work_min: int = 25
    short_break_min: int = 5
    long_break_min: int = 15
    rounds_before_long: int = 4


PHASE_NAMES = {"work": "Odaklanma", "short": "Kısa mola", "long": "Uzun mola"}


class PomodoroCycle:
    """Pomodoro aşamaları: çalışma → kısa mola … (her N turda bir uzun mola)."""

    def __init__(self, config: PomodoroConfig | None = None):
        self.config = config or PomodoroConfig()
        self.phase = "work"
        self.completed_work = 0

    def duration_ms(self, phase: str | None = None) -> int:
        p = phase or self.phase
        minutes = {
            "work": self.config.work_min,
            "short": self.config.short_break_min,
            "long": self.config.long_break_min,
        }[p]
        return int(minutes * 60_000)

    def advance(self) -> str:
        if self.phase == "work":
            self.completed_work += 1
            if self.completed_work % max(1, self.config.rounds_before_long) == 0:
                self.phase = "long"
            else:
                self.phase = "short"
        else:
            self.phase = "work"
        return self.phase

    def reset(self) -> None:
        self.phase = "work"
        self.completed_work = 0

    @property
    def round_in_set(self) -> int:
        """Mevcut setteki çalışma turu (1..N)."""
        n = max(1, self.config.rounds_before_long)
        if self.phase == "work":
            return self.completed_work % n + 1
        return (self.completed_work - 1) % n + 1


# Türkçe etiketli yaygın saat dilimleri
COMMON_ZONES: list[tuple[str, str]] = [
    ("İstanbul", "Europe/Istanbul"),
    ("Londra", "Europe/London"),
    ("Berlin", "Europe/Berlin"),
    ("Paris", "Europe/Paris"),
    ("Moskova", "Europe/Moscow"),
    ("Dubai", "Asia/Dubai"),
    ("Bakü", "Asia/Baku"),
    ("Tahran", "Asia/Tehran"),
    ("Yeni Delhi", "Asia/Kolkata"),
    ("Pekin", "Asia/Shanghai"),
    ("Tokyo", "Asia/Tokyo"),
    ("Seul", "Asia/Seoul"),
    ("Sidney", "Australia/Sydney"),
    ("New York", "America/New_York"),
    ("Chicago", "America/Chicago"),
    ("Los Angeles", "America/Los_Angeles"),
    ("São Paulo", "America/Sao_Paulo"),
    ("Kahire", "Africa/Cairo"),
    ("UTC", "UTC"),
]
DEFAULT_CLOCKS = ["Europe/Istanbul", "Europe/London", "America/New_York", "Asia/Tokyo"]


def zone_label(tz: str) -> str:
    for label, name in COMMON_ZONES:
        if name == tz:
            return label
    return tz.split("/")[-1].replace("_", " ")


def world_time(tz: str, now_utc: datetime | None = None) -> datetime:
    if ZoneInfo is None:
        raise RuntimeError("Saat dilimi desteği yok.")
    now = now_utc or datetime.now(timezone.utc)
    try:
        return now.astimezone(ZoneInfo(tz))
    except ZoneInfoNotFoundError as e:
        raise ValueError(f"Saat dilimi bulunamadı: {tz}") from e


def utc_offset_text(dt: datetime) -> str:
    off = dt.utcoffset()
    if off is None:
        return "UTC"
    total = int(off.total_seconds() // 60)
    sign = "+" if total >= 0 else "-"
    h, m = divmod(abs(total), 60)
    return f"UTC{sign}{h:02d}:{m:02d}"
