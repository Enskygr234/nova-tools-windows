"""Arayüz duman testi: uygulamayı ekransız açar ve tüm sayfaları/işlevleri dener."""
import json
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_full_self_test(tmp_path):
    from PySide6.QtWidgets import QApplication

    from nova_tools.selftest import run_self_test

    app = QApplication.instance() or QApplication([])
    report_path = tmp_path / "report.json"
    code = run_self_test(app, str(report_path))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    failures = [f"{r['test']}: {r.get('error')}\n{r.get('trace', '')}" for r in report["results"] if not r["ok"]]
    assert code == 0, "\n\n".join(failures)
    assert report["total"] >= 9
