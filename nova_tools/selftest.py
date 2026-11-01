"""Kendi kendini doğrulama: uygulamayı açar, tüm sayfaları ve temel işlevleri dener.

Kullanım: NovaTools.exe --self-test=rapor.json
Kullanıcı verisine dokunmaz (geçici veri klasörü kullanır). Çıkış kodu 0 = başarılı.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import traceback


def run_self_test(app, out_path: str = "") -> int:
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QApplication

    tmp = tempfile.mkdtemp(prefix="nova_selftest_")
    os.environ["NOVA_DATA_DIR"] = os.path.join(tmp, "data")
    results: list[dict] = []
    window = None
    storage = None

    def check(name, fn):
        try:
            fn()
            results.append({"test": name, "ok": True})
        except Exception as e:  # noqa: BLE001
            results.append({"test": name, "ok": False, "error": f"{type(e).__name__}: {e}",
                            "trace": traceback.format_exc()})

    def pump(ms: int = 50):
        end = time.time() + ms / 1000
        while time.time() < end:
            QCoreApplication.processEvents()
            time.sleep(0.005)

    try:
        from .core import files as F
        from .core.storage import Storage
        from .ui.main_window import NAV_ITEMS, MainWindow

        storage = Storage()
        window = MainWindow(storage)
        window.show()
        pump(200)
        check("pencere açıldı", lambda: _assert(window.isVisible(), "pencere görünür değil"))

        def all_pages():
            for key, _ in NAV_ITEMS:
                window.navigate(key)
                pump(30)
                _assert(window.stack.currentWidget() is window.pages[key], f"{key} açılmadı")
                tabs = getattr(window.pages[key], "tabs", None)
                if tabs is not None:
                    for i in range(tabs.count()):
                        tabs.setCurrentIndex(i)
                        pump(10)
        check("tüm sayfalar ve sekmeler", all_pages)

        calc = window.pages["calc"]

        def calculator():
            c = calc.calculator
            for k in ["AC", "2", "+", "3", "×", "4", "="]:
                c.press(k)
            _assert(c.result.text() == "14", f"hesap sonucu {c.result.text()}")
            c.expr.setText("sin(30)")
            c.equals()
            _assert(c.result.text() == "0,5", f"sin sonucu {c.result.text()}")
        check("bilimsel hesap makinesi", calculator)

        def converter():
            cv = calc.converter
            cv.cat.setCurrentText("Sıcaklık")
            cv.src.setCurrentText("Santigrat (°C)")
            cv.dst.setCurrentText("Fahrenhayt (°F)")
            cv.value.setValue(100)
            _assert(cv.out.text().startswith("212"), cv.out.text())
        check("birim dönüştürücü", converter)

        def sha():
            calc.hash.text.setPlainText("abc")
            _assert(calc.hash.text_hash.text().startswith("ba7816bf"), "sha256 yanlış")
        check("SHA-256", sha)

        text = window.pages["text"]

        def text_tools():
            text.counter.input.setPlainText("Merhaba dünya. İkinci cümle!")
            _assert(text.counter.values["words"].text() == "4", "kelime sayısı")
            text.json.input.setPlainText('{"b":1,"a":2}')
            text.json.sort.setChecked(True)
            text.json.format()
            _assert(text.json.output.toPlainText().startswith('{\n  "a"'), "json biçimlendirme")
            text.b64.input.setPlainText("Nova ğüş")
            text.b64.encode()
            text.b64.swap()
            text.b64.decode()
            _assert(text.b64.output.toPlainText() == "Nova ğüş", "base64")
            text.compare.left.setPlainText("a\nb")
            text.compare.right.setPlainText("a\nc")
            text.compare.compare()
            _assert("+1" in text.compare.summary.text(), text.compare.summary.text())
            text.editor.edit.setPlainText("deneme")
            path = os.path.join(tmp, "editor.txt")
            _assert(text.editor._write(path), "editör kaydetme")
            text.editor.edit.clear()
            _assert(text.editor.load(path) and text.editor.edit.toPlainText() == "deneme", "editör açma")
        check("metin araçları", text_tools)

        def notes():
            n = window.pages["notes"]
            window.navigate("notes")
            n.new_note()
            n.title.setText("Self-test notu")
            n.body.setPlainText("İçerik")
            n.save_current()
            _assert(any(x.title == "Self-test notu" for x in storage.list_notes()), "not kaydedilmedi")
            n.new_note()
            _assert(storage.note_count() == 2, "ikinci not")
            first = [x for x in storage.list_notes() if x.title == "Self-test notu"][0]
            _assert(first.content == "İçerik", "ilk not bozuldu")
        check("notlar ve otomatik kaydetme", notes)

        def file_tools():
            root = os.path.join(tmp, "files")
            os.makedirs(os.path.join(root, "alt"))
            for p in ("a.txt", os.path.join("alt", "b.txt")):
                with open(os.path.join(root, p), "w", encoding="utf-8") as fh:
                    fh.write("aynı içerik")
            fp = window.pages["files"]
            fp.search.show_result(F.search_files(root, "*.txt"))
            _assert(fp.search.table.rowCount() == 2, "arama sonucu")
            fp.dups.show_result(F.find_duplicates(root))
            _assert(fp.dups.tree.topLevelItemCount() == 1, "yinelenen")
            fp.folder.show_result(F.analyze_folder(root))
            fp.ext.show_result(F.extension_stats(root))
            # Arka plan işçisi gerçekten çalışıyor mu?
            fp.search.picker.set_path(root)
            fp.search.pattern.setText("b.txt")
            fp.search.start()
            deadline = time.time() + 10
            while fp.search.worker is not None and time.time() < deadline:
                pump(20)
            _assert(fp.search.table.rowCount() == 1, "arka plan arama")
        check("dosya araçları", file_tools)

        def time_tools():
            tp = window.pages["time"]
            tp.stopwatch.toggle()
            pump(120)
            tp.stopwatch.toggle()
            _assert(tp.stopwatch.current_ms() > 0, "kronometre")
            tp.pomodoro.toggle()
            pump(50)
            tp.pomodoro.reset()
            _assert(len(tp.clocks.cards) >= 1, "dünya saatleri")
            tp.clocks.refresh()
            _assert(tp.clocks.cards[0][2].text() != "--:--:--", "saat güncellenmedi")
        check("zaman araçları", time_tools)

        def theme_and_backup():
            window.apply_theme("light")
            pump(30)
            window.apply_theme("dark")
            target = os.path.join(tmp, "yedek.db")
            storage.backup_to(target)
            _assert(Storage.validate_backup(target) == storage.note_count(), "yedek")
        check("tema ve yedekleme", theme_and_backup)

        def dashboard():
            window.navigate("dashboard")
            pump(30)
            d = window.pages["dashboard"]
            _assert(d.recent_list.count() >= 1, "son kullanılanlar")
            d.cards[6]._on_click()
            _assert(window.current_key == "calc", "hızlı erişim kartı")
        check("ana sayfa", dashboard)

        shot_dir = os.environ.get("NOVA_SCREENSHOT_DIR")
        if shot_dir:
            def screenshots():
                os.makedirs(shot_dir, exist_ok=True)
                window.resize(1280, 800)
                saved = 0
                for i, (key, _) in enumerate(NAV_ITEMS):
                    window.navigate(key)
                    pump(450)
                    if window.grab().save(os.path.join(shot_dir, f"{i + 1:02d}_{key}.png")):
                        saved += 1
                _assert(saved == len(NAV_ITEMS), "ekran görüntüsü kaydedilemedi")
            check("ekran görüntüleri", screenshots)
    except Exception as e:  # noqa: BLE001
        results.append({"test": "başlatma", "ok": False, "error": str(e), "trace": traceback.format_exc()})
    finally:
        if window is not None:
            for page in window.pages.values():
                if hasattr(page, "shutdown"):
                    page.shutdown()
            window.hide()
            window.deleteLater()
        if storage is not None:
            storage.close()
        QApplication.processEvents()
        shutil.rmtree(tmp, ignore_errors=True)

    ok = all(r["ok"] for r in results)
    report = {"ok": ok, "passed": sum(r["ok"] for r in results), "total": len(results), "results": results}
    text_out = json.dumps(report, ensure_ascii=False, indent=2)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text_out)
    else:
        try:
            print(text_out)
        except Exception:  # noqa: BLE001  (pencereli exe'de stdout olmayabilir)
            pass
    return 0 if ok else 1


def _assert(cond, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)
