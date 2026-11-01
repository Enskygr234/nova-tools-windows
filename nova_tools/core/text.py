"""Metin araçları: sayaçlar, karşılaştırma, JSON, Base64."""
from __future__ import annotations

import base64
import binascii
import difflib
import html
import json
import re
from dataclasses import dataclass

_WORD_RE = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)
_SENTENCE_RE = re.compile(r"[^.!?…]+[.!?…]+|[^.!?…]+$", re.UNICODE)


def tr_fold(s: str) -> str:
    """Türkçe kurallara uygun küçük harfe çevirme (İ→i, I→ı)."""
    return s.replace("İ", "i").replace("I", "ı").lower()


@dataclass
class TextStats:
    words: int
    chars: int
    chars_no_spaces: int
    letters: int
    digits: int
    lines: int
    sentences: int
    paragraphs: int
    reading_minutes: float
    unique_words: int


def text_stats(text: str) -> TextStats:
    words = _WORD_RE.findall(text)
    stripped = text.strip()
    sentences = [s for s in _SENTENCE_RE.findall(stripped) if s.strip()] if stripped else []
    paragraphs = [p for p in re.split(r"\n\s*\n", stripped) if p.strip()] if stripped else []
    return TextStats(
        words=len(words),
        chars=len(text),
        chars_no_spaces=sum(1 for c in text if not c.isspace()),
        letters=sum(1 for c in text if c.isalpha()),
        digits=sum(1 for c in text if c.isdigit()),
        lines=0 if text == "" else text.count("\n") + 1,
        sentences=len(sentences),
        paragraphs=len(paragraphs),
        reading_minutes=round(len(words) / 200, 1),
        unique_words=len({w.casefold() for w in words}),
    )


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def char_count(text: str, include_spaces: bool = True) -> int:
    return len(text) if include_spaces else sum(1 for c in text if not c.isspace())


def top_words(text: str, n: int = 10, min_len: int = 3) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for w in _WORD_RE.findall(text):
        key = w.casefold()
        if len(key) >= min_len:
            counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


# ---------- Karşılaştırma ----------
@dataclass
class DiffResult:
    lines: list[tuple[str, str]]  # (etiket, satır) etiket: ' ', '+', '-'
    added: int
    removed: int
    similarity: float


def diff_texts(a: str, b: str, ignore_case: bool = False, ignore_whitespace: bool = False) -> DiffResult:
    def norm(s: str) -> str:
        if ignore_whitespace:
            s = " ".join(s.split())
        if ignore_case:
            s = s.casefold()
        return s

    la, lb = a.splitlines(), b.splitlines()
    na, nb = [norm(x) for x in la], [norm(x) for x in lb]
    sm = difflib.SequenceMatcher(None, na, nb, autojunk=False)
    out: list[tuple[str, str]] = []
    added = removed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.extend((" ", line) for line in la[i1:i2])
        else:
            if tag in ("replace", "delete"):
                out.extend(("-", line) for line in la[i1:i2])
                removed += i2 - i1
            if tag in ("replace", "insert"):
                out.extend(("+", line) for line in lb[j1:j2])
                added += j2 - j1
    ratio = difflib.SequenceMatcher(None, norm(a), norm(b), autojunk=False).ratio() if (a or b) else 1.0
    return DiffResult(out, added, removed, ratio)


def diff_to_html(result: DiffResult, dark: bool = True) -> str:
    add_bg, del_bg = ("#123d2a", "#4a1720") if dark else ("#d9f7e6", "#fde2e4")
    fg = "#e8e8f0" if dark else "#16162a"
    rows = []
    for tag, line in result.lines:
        esc = html.escape(line) or "&nbsp;"
        if tag == "+":
            rows.append(f'<div style="background:{add_bg}">+ {esc}</div>')
        elif tag == "-":
            rows.append(f'<div style="background:{del_bg}">- {esc}</div>')
        else:
            rows.append(f"<div>&nbsp;&nbsp;{esc}</div>")
    return (f'<div style="font-family:Consolas,monospace;font-size:10pt;color:{fg};'
            f'white-space:pre-wrap">{"".join(rows)}</div>')


# ---------- JSON ----------
class TextToolError(ValueError):
    """Kullanıcıya gösterilecek Türkçe hata."""


def format_json(text: str, indent: int = 2, sort_keys: bool = False) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise TextToolError(f"Geçersiz JSON: {e.msg} (satır {e.lineno}, sütun {e.colno})") from e
    return json.dumps(data, indent=indent, ensure_ascii=False, sort_keys=sort_keys)


def minify_json(text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise TextToolError(f"Geçersiz JSON: {e.msg} (satır {e.lineno}, sütun {e.colno})") from e
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


# ---------- Base64 ----------
def b64_encode(text: str, url_safe: bool = False) -> str:
    raw = text.encode("utf-8")
    return (base64.urlsafe_b64encode(raw) if url_safe else base64.b64encode(raw)).decode("ascii")


def b64_decode(text: str, url_safe: bool = False) -> str:
    cleaned = "".join(text.split())
    if not cleaned:
        return ""
    cleaned += "=" * (-len(cleaned) % 4)
    try:
        raw = (base64.urlsafe_b64decode(cleaned) if url_safe
               else base64.b64decode(cleaned, validate=True))
    except (binascii.Error, ValueError) as e:
        raise TextToolError("Geçersiz Base64 verisi.") from e
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise TextToolError("Çözülen veri UTF-8 metin değil (ikili veri olabilir).") from e
