import json
import math
import os
import threading
from datetime import datetime, timezone

import pytest

from nova_tools.core import calc, files, text, timeutil, units
from nova_tools.core.storage import Storage


# ---------------- Dosya araçları ----------------
@pytest.fixture()
def tree(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b").mkdir()
    (tmp_path / "bos").mkdir()
    (tmp_path / "rapor.txt").write_text("merhaba dünya", encoding="utf-8")
    (tmp_path / "a" / "kopya.txt").write_text("merhaba dünya", encoding="utf-8")
    (tmp_path / "a" / "b" / "resim.PNG").write_bytes(b"\x89PNG" + b"0" * 2000)
    big = os.urandom(200_000)
    (tmp_path / "buyuk1.bin").write_bytes(big)
    (tmp_path / "a" / "buyuk2.bin").write_bytes(big)
    # aynı boyut, farklı son bayt -> kopya DEĞİL
    (tmp_path / "a" / "b" / "buyuk3.bin").write_bytes(big[:-1] + bytes([(big[-1] + 1) % 256]))
    return tmp_path


def test_human_size():
    assert files.human_size(0) == "0 B"
    assert files.human_size(1536) == "1,50 KB"
    assert files.human_size(5 * 1024 ** 3) == "5,00 GB"


def test_iter_files_counts_all(tree):
    assert len(list(files.iter_files(str(tree)))) == 6


def test_iter_files_missing_dir():
    with pytest.raises(FileNotFoundError):
        list(files.iter_files("/olmayan/klasor/xyz"))


def test_search_by_name_ext_size(tree):
    names = lambda res: sorted(os.path.basename(r.path) for r in res)
    assert names(files.search_files(str(tree), "kopya")) == ["kopya.txt"]
    assert names(files.search_files(str(tree), "*.txt")) == ["kopya.txt", "rapor.txt"]
    assert names(files.search_files(str(tree), extensions="png")) == ["resim.PNG"]
    assert names(files.search_files(str(tree), "rapor;resim")) == ["rapor.txt", "resim.PNG"]
    assert len(files.search_files(str(tree), min_size=100_000)) == 3
    assert len(files.search_files(str(tree), limit=2)) == 2


def test_find_duplicates(tree):
    groups = files.find_duplicates(str(tree))
    as_sets = [sorted(os.path.basename(p) for p in g.paths) for g in groups]
    assert ["buyuk1.bin", "buyuk2.bin"] in as_sets
    assert ["kopya.txt", "rapor.txt"] in as_sets
    assert len(groups) == 2
    assert groups[0].wasted == 200_000  # en çok yer kaplayan önce


def test_find_duplicates_does_not_modify(tree):
    before = {p: os.path.getmtime(p) for p in (str(e.path) for e in files.iter_files(str(tree)))}
    files.find_duplicates(str(tree))
    after = {p: os.path.getmtime(p) for p in (str(e.path) for e in files.iter_files(str(tree)))}
    assert before == after


def test_cancel(tree):
    ev = threading.Event()
    ev.set()
    with pytest.raises(files.Cancelled):
        files.find_duplicates(str(tree), cancel=ev)


def test_analyze_folder(tree):
    rep = files.analyze_folder(str(tree))
    assert rep.file_count == 6
    assert rep.total_size == sum(e.size for e in files.iter_files(str(tree)))
    names = {c[0]: c for c in rep.children}
    assert names["a"][3] is True and names["a"][2] == 4
    assert names["bos"][1] == 0
    assert rep.largest[0].size == 200_000


def test_extension_stats(tree):
    stats = {s.extension: s for s in files.extension_stats(str(tree))}
    assert stats[".bin"].count == 3
    assert stats[".txt"].count == 2
    assert stats[".png"].count == 1


def test_sha256_file(tree):
    p = tree / "rapor.txt"
    assert files.sha256_file(str(p)) == calc.sha256_text("merhaba dünya")


# ---------------- Metin araçları ----------------
def test_text_stats_turkish():
    s = text.text_stats("Merhaba dünya! Bugün hava çok güzel.\n\nİkinci paragraf, 2026 yılı.")
    assert s.words == 10
    assert s.sentences == 3
    assert s.paragraphs == 2
    assert s.lines == 3
    assert s.digits == 4
    assert s.chars == len("Merhaba dünya! Bugün hava çok güzel.\n\nİkinci paragraf, 2026 yılı.")


def test_counts_empty():
    s = text.text_stats("")
    assert (s.words, s.chars, s.lines, s.sentences) == (0, 0, 0, 0)
    assert text.char_count("a b c", include_spaces=False) == 3
    assert text.word_count("çağ-dışı ve O'Neil") == 3


def test_diff():
    r = text.diff_texts("a\nb\nc", "a\nB\nc\nd")
    assert r.added == 2 and r.removed == 1
    assert ("-", "b") in r.lines and ("+", "d") in r.lines
    r2 = text.diff_texts("Elma", "elma", ignore_case=True)
    assert r2.added == 0 and r2.similarity == 1.0
    assert "background" in text.diff_to_html(r)


def test_json_format_and_errors():
    out = text.format_json('{"b":1,"a":[1,2],"ş":"ğ"}', indent=2, sort_keys=True)
    assert json.loads(out) == {"a": [1, 2], "b": 1, "ş": "ğ"}
    assert "ğ" in out and out.index('"a"') < out.index('"b"')
    assert text.minify_json('{ "a" : 1 }') == '{"a":1}'
    with pytest.raises(text.TextToolError, match="satır 1"):
        text.format_json("{a:1}")


def test_base64_roundtrip():
    for s in ["Merhaba Dünya ğüşıöç", "", "a"]:
        assert text.b64_decode(text.b64_encode(s)) == s
        assert text.b64_decode(text.b64_encode(s, True), True) == s
    assert text.b64_decode("TWVyaGFiYQ") == "Merhaba"  # eksik dolgu
    with pytest.raises(text.TextToolError):
        text.b64_decode("@@@")


# ---------------- Hesap makinesi ----------------
@pytest.mark.parametrize("expr,expected", [
    ("2+3*4", 14), ("(2+3)*4", 20), ("2^10", 1024), ("10/4", 2.5), ("7//2", 3),
    ("-3+5", 2), ("3,5*2", 7), ("50%*200", 100), ("5!", 120), ("sqrt(16)", 4),
    ("sin(30)", 0.5), ("cos(60)", 0.5), ("log(1000)", 3), ("ln(e)", 1), ("2×3÷4", 1.5),
    ("pi", math.pi), ("abs(-7)", 7), ("√9", 3),
])
def test_evaluate(expr, expected):
    assert calc.evaluate(expr) == pytest.approx(expected)


def test_evaluate_radians():
    assert calc.evaluate("sin(pi/2)", "rad") == pytest.approx(1)


@pytest.mark.parametrize("expr", [
    "1/0", "__import__('os')", "2**99999", "sqrt(-1)", "log(0)", "foo(2)", "", "(1+",
    "().__class__", "tan(90)", "fact(-1)", "a=1",
])
def test_evaluate_rejects(expr):
    with pytest.raises(calc.CalcError):
        calc.evaluate(expr)


def test_format_number():
    assert calc.format_number(14) == "14"
    assert calc.format_number(2.5) == "2,5"
    assert calc.format_number(1 / 3) == "0,333333333333"
    assert "e" in calc.format_number(1e20)


def test_sha256_known():
    assert calc.sha256_text("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


# ---------------- Birim dönüştürücü ----------------
def test_units():
    assert units.convert("Uzunluk", 1, "Kilometre (km)", "Metre (m)") == pytest.approx(1000)
    assert units.convert("Uzunluk", 1, "Mil (mi)", "Kilometre (km)") == pytest.approx(1.609344)
    assert units.convert("Sıcaklık", 100, "Santigrat (°C)", "Fahrenhayt (°F)") == pytest.approx(212)
    assert units.convert("Sıcaklık", 0, "Kelvin (K)", "Santigrat (°C)") == pytest.approx(-273.15)
    assert units.convert("Veri", 1, "Gigabayt (GB)", "Megabayt (MB)") == pytest.approx(1024)
    assert units.convert("Hız", 36, "km/sa", "m/s") == pytest.approx(10)
    with pytest.raises(ValueError):
        units.convert("Sıcaklık", -300, "Santigrat (°C)", "Kelvin (K)")
    for cat, table in units.UNITS.items():
        u = list(table)
        assert units.convert(cat, 12.5, u[0], u[0]) == pytest.approx(12.5)


# ---------------- Zaman ----------------
def test_format_duration():
    assert timeutil.format_duration(3_723_450) == "01:02:03.45"
    assert timeutil.format_duration(59_999, show_centis=False) == "00:00:59"


def test_pomodoro_cycle():
    p = timeutil.PomodoroCycle(timeutil.PomodoroConfig(25, 5, 15, 4))
    phases = [p.advance() for _ in range(8)]
    assert phases == ["short", "work", "short", "work", "short", "work", "long", "work"]
    assert p.duration_ms("long") == 15 * 60_000
    p.reset()
    assert p.phase == "work" and p.round_in_set == 1


def test_world_time():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    ist = timeutil.world_time("Europe/Istanbul", now)
    assert ist.hour == 15
    assert timeutil.utc_offset_text(ist) == "UTC+03:00"
    with pytest.raises(ValueError):
        timeutil.world_time("Mars/Olympus", now)


# ---------------- Depolama ----------------
def test_storage_notes_settings_backup(tmp_path):
    db = Storage(str(tmp_path / "data" / "n.db"))
    nid = db.add_note("İlk not", "İstanbul’da ılık bir gün", "Kişisel")
    db.add_note("İkinci", "iş listesi", "İş")
    assert db.note_count() == 2
    assert [n.id for n in db.list_notes("istanbul")] == [nid]  # Türkçe büyük/küçük harf
    assert [n.title for n in db.list_notes(category="İş")] == ["İkinci"]
    db.update_note(nid, "Güncel", "yeni", "Kişisel")
    assert db.get_note(nid).title == "Güncel"
    assert set(db.categories()) == {"Kişisel", "İş"}

    db.set("theme", "light")
    assert db.get("theme") == "light"
    assert db.get("yok", "varsayılan") == "varsayılan"

    db.touch_tool("calc")
    db.touch_tool("text")
    db.touch_tool("calc")
    rec = db.recent_tools()
    assert rec[0][0] == "calc" and rec[0][2] == 2

    backup = str(tmp_path / "yedek.db")
    db.backup_to(backup)
    assert Storage.validate_backup(backup) == 2
    db.delete_note(nid)
    assert db.note_count() == 1
    db.restore_from(backup)
    assert db.note_count() == 2
    with pytest.raises(ValueError):
        db.backup_to(db.path)

    bad = tmp_path / "bozuk.db"
    bad.write_text("sqlite değil")
    with pytest.raises(ValueError):
        Storage.validate_backup(str(bad))
    db.close()
