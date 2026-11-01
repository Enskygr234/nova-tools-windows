"""Dosya analiz araçları. Bu modül hiçbir dosyayı değiştirmez veya silmez."""
from __future__ import annotations

import fnmatch
import hashlib
import os
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Iterator, Optional

ProgressCb = Optional[Callable[[str], None]]
CHUNK = 1024 * 1024
PARTIAL = 64 * 1024


class Cancelled(Exception):
    """İşlem kullanıcı tarafından durduruldu."""


def human_size(n: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(n)
    for unit in units:
        if abs(size) < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}".replace(".", ",")
        size /= 1024
    return f"{size:.2f} PB"


@dataclass
class FileEntry:
    path: str
    size: int
    mtime: float


def _check(cancel: Optional[threading.Event]) -> None:
    if cancel is not None and cancel.is_set():
        raise Cancelled()


def iter_files(root: str, cancel: Optional[threading.Event] = None,
               progress: ProgressCb = None) -> Iterator[FileEntry]:
    """Klasördeki tüm dosyaları (alt klasörler dahil) gezer.

    Erişim izni olmayan klasörler sessizce atlanır, sembolik bağlantılar izlenmez.
    """
    if not os.path.isdir(root):
        raise FileNotFoundError(f"Klasör bulunamadı: {root}")
    stack = [root]
    scanned = 0
    while stack:
        _check(cancel)
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                entries = list(it)
        except (PermissionError, FileNotFoundError, NotADirectoryError, OSError):
            continue
        for entry in entries:
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    st = entry.stat(follow_symlinks=False)
                    scanned += 1
                    if progress and scanned % 500 == 0:
                        _check(cancel)
                        progress(f"{scanned} dosya tarandı…")
                    yield FileEntry(entry.path, st.st_size, st.st_mtime)
            except OSError:
                continue


def _matches(name: str, pattern: str) -> bool:
    pattern = pattern.strip()
    if not pattern:
        return True
    low_name = name.lower()
    for part in [p.strip().lower() for p in pattern.split(";") if p.strip()]:
        if any(ch in part for ch in "*?["):
            if fnmatch.fnmatch(low_name, part):
                return True
        elif part in low_name:
            return True
    return False


def search_files(root: str, pattern: str = "", extensions: str = "",
                 min_size: int = 0, max_size: Optional[int] = None,
                 limit: int = 5000, cancel: Optional[threading.Event] = None,
                 progress: ProgressCb = None) -> list[FileEntry]:
    """Ada (alt metin veya joker; ';' ile çoklu), uzantıya ve boyuta göre arama."""
    exts = {e.strip().lower().lstrip(".") for e in extensions.replace(",", ";").split(";") if e.strip()}
    results: list[FileEntry] = []
    for f in iter_files(root, cancel, progress):
        name = os.path.basename(f.path)
        if exts and os.path.splitext(name)[1].lower().lstrip(".") not in exts:
            continue
        if f.size < min_size or (max_size is not None and f.size > max_size):
            continue
        if not _matches(name, pattern):
            continue
        results.append(f)
        if len(results) >= limit:
            break
    return results


def sha256_file(path: str, cancel: Optional[threading.Event] = None,
                progress: Optional[Callable[[int, int], None]] = None,
                limit: Optional[int] = None) -> str:
    h = hashlib.sha256()
    total = os.path.getsize(path)
    done = 0
    with open(path, "rb") as fh:
        while True:
            _check(cancel)
            to_read = CHUNK if limit is None else min(CHUNK, limit - done)
            if to_read <= 0:
                break
            chunk = fh.read(to_read)
            if not chunk:
                break
            h.update(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    return h.hexdigest()


@dataclass
class DuplicateGroup:
    size: int
    digest: str
    paths: list[str] = field(default_factory=list)

    @property
    def wasted(self) -> int:
        return self.size * (len(self.paths) - 1)


def find_duplicates(root: str, min_size: int = 1, cancel: Optional[threading.Event] = None,
                    progress: ProgressCb = None) -> list[DuplicateGroup]:
    """Aynı içerikli dosyaları bulur: boyut → ilk 64 KB özeti → tam SHA-256."""
    by_size: dict[int, list[str]] = defaultdict(list)
    for f in iter_files(root, cancel, progress):
        if f.size >= min_size:
            by_size[f.size].append(f.path)

    candidates = [(s, p) for s, p in by_size.items() if len(p) > 1]
    groups: list[DuplicateGroup] = []
    total = sum(len(p) for _, p in candidates)
    checked = 0
    for size, paths in candidates:
        partial: dict[str, list[str]] = defaultdict(list)
        for p in paths:
            _check(cancel)
            checked += 1
            if progress and checked % 50 == 0:
                progress(f"İçerik karşılaştırılıyor: {checked}/{total}")
            try:
                partial[sha256_file(p, cancel, limit=PARTIAL)].append(p)
            except OSError:
                continue
        for partial_digest, same in partial.items():
            if len(same) < 2:
                continue
            if size <= PARTIAL:
                # Kısmi özet zaten dosyanın tamamını kapsıyor.
                groups.append(DuplicateGroup(size, partial_digest, sorted(same)))
                continue
            full: dict[str, list[str]] = defaultdict(list)
            for p in same:
                try:
                    full[sha256_file(p, cancel)].append(p)
                except OSError:
                    continue
            for digest, ps in full.items():
                if len(ps) > 1:
                    groups.append(DuplicateGroup(size, digest, sorted(ps)))
    groups.sort(key=lambda g: g.wasted, reverse=True)
    return groups


@dataclass
class FolderReport:
    root: str
    total_size: int
    file_count: int
    folder_count: int
    children: list[tuple[str, int, int, bool]]  # (ad, boyut, dosya sayısı, klasör mü)
    largest: list[FileEntry]


def analyze_folder(root: str, top_n: int = 100, cancel: Optional[threading.Event] = None,
                   progress: ProgressCb = None) -> FolderReport:
    """Klasörün toplam boyutu, alt öğe boyutları ve en büyük dosyaları."""
    root = os.path.abspath(root)
    child_sizes: dict[str, list[int]] = {}
    folders: set[str] = set()
    largest: list[FileEntry] = []
    total = 0
    count = 0
    for f in iter_files(root, cancel, progress):
        total += f.size
        count += 1
        rel = os.path.relpath(f.path, root)
        parts = rel.split(os.sep)
        top = parts[0]
        is_dir = len(parts) > 1
        rec = child_sizes.setdefault(top, [0, 0, int(is_dir)])
        rec[0] += f.size
        rec[1] += 1
        for i in range(1, len(parts)):
            folders.add(os.sep.join(parts[:i]))
        largest.append(f)
        if len(largest) > top_n * 4:
            largest.sort(key=lambda e: e.size, reverse=True)
            del largest[top_n:]
    # Boş alt klasörleri de listele
    try:
        with os.scandir(root) as it:
            for e in it:
                if e.is_dir(follow_symlinks=False) and e.name not in child_sizes:
                    child_sizes[e.name] = [0, 0, 1]
                    folders.add(e.name)
    except OSError:
        pass
    largest.sort(key=lambda e: e.size, reverse=True)
    children = sorted(((n, v[0], v[1], bool(v[2])) for n, v in child_sizes.items()),
                      key=lambda c: c[1], reverse=True)
    return FolderReport(root, total, count, len(folders), children, largest[:top_n])


@dataclass
class ExtensionStat:
    extension: str
    count: int
    total_size: int


def extension_stats(root: str, cancel: Optional[threading.Event] = None,
                    progress: ProgressCb = None) -> list[ExtensionStat]:
    stats: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for f in iter_files(root, cancel, progress):
        ext = os.path.splitext(f.path)[1].lower() or "(uzantısız)"
        stats[ext][0] += 1
        stats[ext][1] += f.size
    return sorted((ExtensionStat(e, v[0], v[1]) for e, v in stats.items()),
                  key=lambda s: s.total_size, reverse=True)
