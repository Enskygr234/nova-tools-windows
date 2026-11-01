"""Dosya araçları: arama, yinelenen dosyalar, klasör/boyut analizi, uzantı analizi."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu,
    QProgressBar, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ...core import files as F
from ..widgets import (
    Card, FolderPicker, Worker, confirm, error, info, muted_label, open_path, page_header,
    primary_button, show_in_explorer,
)

SIZE_UNITS = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}


class SizeItem(QTableWidgetItem):
    """Boyuta göre doğru sıralama için sayısal veri taşıyan hücre."""

    def __init__(self, size: int):
        super().__init__(F.human_size(size))
        self.setData(Qt.UserRole, size)
        self.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def __lt__(self, other):  # noqa: D105
        return (self.data(Qt.UserRole) or 0) < (other.data(Qt.UserRole) or 0)


def make_table(headers: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setAlternatingRowColors(True)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    for i in range(1, len(headers)):
        t.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
    t.setSortingEnabled(True)
    t.setContextMenuPolicy(Qt.CustomContextMenu)
    return t


def attach_path_menu(table: QTableWidget, path_col: int = 0) -> None:
    def menu(pos):
        item = table.itemAt(pos)
        if item is None:
            return
        path = table.item(item.row(), path_col).data(Qt.UserRole) or table.item(item.row(), path_col).text()
        m = QMenu(table)
        m.addAction("Klasörde göster", lambda: show_in_explorer(path))
        if os.path.isfile(path):
            m.addAction("Aç", lambda: open_path(path))
        m.exec(table.viewport().mapToGlobal(pos))

    table.customContextMenuRequested.connect(menu)
    table.itemDoubleClicked.connect(
        lambda it: show_in_explorer(table.item(it.row(), path_col).data(Qt.UserRole) or table.item(it.row(), path_col).text())
    )


class ScanTab(QWidget):
    """Klasör seçimi + Başlat/Durdur + ilerleme çubuğu içeren ortak sekme tabanı."""

    def __init__(self, main, description: str):
        super().__init__()
        self.main = main
        self.worker: Optional[Worker] = None
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 10, 0, 0)
        self.lay.setSpacing(10)
        self.lay.addWidget(muted_label(description))
        self.picker = FolderPicker()
        self.picker.set_path(os.path.expanduser("~"))
        self.options = QHBoxLayout()
        self.start_btn = primary_button("Başlat")
        self.stop_btn = QPushButton("Durdur")
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setMaximumHeight(8)
        self.status = muted_label("Hazır")
        top = Card()
        top.body.addWidget(self.picker)
        top.body.addLayout(self.options)
        btns = QHBoxLayout()
        btns.addWidget(self.start_btn)
        btns.addWidget(self.stop_btn)
        btns.addStretch(1)
        top.body.addLayout(btns)
        top.body.addWidget(self.progress)
        top.body.addWidget(self.status)
        self.lay.addWidget(top)

    # Alt sınıflar uygular
    def job(self, root: str) -> Callable:
        raise NotImplementedError

    def show_result(self, result) -> None:
        raise NotImplementedError

    def start(self) -> None:
        root = self.picker.path()
        if not root or not os.path.isdir(root):
            error(self, "Lütfen geçerli bir klasör seçin.")
            return
        try:
            fn = self.job(root)
        except ValueError as e:
            error(self, str(e))
            return
        self.worker = Worker(fn, self)
        self.worker.progress.connect(self.status.setText)
        self.worker.succeeded.connect(self._done)
        self.worker.failed.connect(self._failed)
        self.worker.cancelled.connect(self._cancelled)
        self.worker.finished.connect(self._finished)
        self.progress.setRange(0, 0)  # belirsiz ilerleme animasyonu
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status.setText("Taranıyor…")
        self.worker.start()

    def stop(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.status.setText("Durduruluyor…")

    def _done(self, result) -> None:
        self.show_result(result)

    def _failed(self, msg: str) -> None:
        self.status.setText("Hata: " + msg)
        error(self, msg)

    def _cancelled(self) -> None:
        self.status.setText("İşlem durduruldu.")

    def _finished(self) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.worker = None

    def shutdown(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.worker.wait(3000)


class SearchTab(ScanTab):
    def __init__(self, main):
        super().__init__(main, "Ada (ör. rapor, *.pdf; birden çok için ';'), uzantıya ve boyuta göre dosya arayın.")
        self.pattern = QLineEdit()
        self.pattern.setPlaceholderText("Dosya adı veya desen (ör. *.docx;fatura)")
        self.exts = QLineEdit()
        self.exts.setPlaceholderText("Uzantılar (ör. jpg;png)")
        self.min_size = QSpinBox()
        self.min_size.setRange(0, 10_000_000)
        self.min_unit = QComboBox()
        self.min_unit.addItems(list(SIZE_UNITS))
        self.min_unit.setCurrentText("KB")
        self.options.addWidget(self.pattern, 2)
        self.options.addWidget(self.exts, 1)
        self.options.addWidget(QLabel("En az:"))
        self.options.addWidget(self.min_size)
        self.options.addWidget(self.min_unit)
        self.pattern.returnPressed.connect(self.start)
        self.table = make_table(["Dosya", "Boyut", "Değiştirilme"])
        attach_path_menu(self.table)
        self.lay.addWidget(self.table, 1)

    def job(self, root):
        pattern, exts = self.pattern.text(), self.exts.text()
        min_size = self.min_size.value() * SIZE_UNITS[self.min_unit.currentText()]
        return lambda cancel, progress: F.search_files(root, pattern, exts, min_size, None, 5000, cancel, progress)

    def show_result(self, result) -> None:
        t = self.table
        t.setSortingEnabled(False)
        t.setRowCount(len(result))
        for r, e in enumerate(result):
            item = QTableWidgetItem(e.path)
            item.setData(Qt.UserRole, e.path)
            t.setItem(r, 0, item)
            t.setItem(r, 1, SizeItem(e.size))
            t.setItem(r, 2, QTableWidgetItem(datetime.fromtimestamp(e.mtime).strftime("%d.%m.%Y %H:%M")))
        t.setSortingEnabled(True)
        extra = " (ilk 5000 sonuç)" if len(result) >= 5000 else ""
        self.status.setText(f"{len(result)} dosya bulundu{extra}. Çift tıklayınca klasörde gösterilir.")


class DuplicatesTab(ScanTab):
    def __init__(self, main):
        super().__init__(main, "Aynı içeriğe sahip dosyaları SHA-256 ile tespit eder. Hiçbir dosya otomatik silinmez.")
        self.min_size = QSpinBox()
        self.min_size.setRange(0, 10_000_000)
        self.min_size.setValue(1)
        self.min_unit = QComboBox()
        self.min_unit.addItems(list(SIZE_UNITS))
        self.min_unit.setCurrentText("KB")
        self.options.addWidget(QLabel("En küçük dosya boyutu:"))
        self.options.addWidget(self.min_size)
        self.options.addWidget(self.min_unit)
        self.options.addStretch(1)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Dosya", "Boyut"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self._reveal)
        self.lay.addWidget(self.tree, 1)
        row = QHBoxLayout()
        self.trash_btn = QPushButton("🗑  İşaretlileri Geri Dönüşüm Kutusu'na taşı")
        self.trash_btn.setObjectName("Danger")
        self.trash_btn.setEnabled(False)
        self.trash_btn.clicked.connect(self._trash_checked)
        self.select_btn = QPushButton("Her grupta ilki hariç işaretle")
        self.select_btn.setEnabled(False)
        self.select_btn.clicked.connect(self._check_all_but_first)
        row.addWidget(self.select_btn)
        row.addWidget(self.trash_btn)
        row.addStretch(1)
        self.lay.addLayout(row)

    def job(self, root):
        min_size = max(1, self.min_size.value() * SIZE_UNITS[self.min_unit.currentText()])
        return lambda cancel, progress: F.find_duplicates(root, min_size, cancel, progress)

    def show_result(self, groups) -> None:
        self.tree.clear()
        wasted = 0
        for i, g in enumerate(groups, 1):
            wasted += g.wasted
            parent = QTreeWidgetItem([f"Grup {i} — {len(g.paths)} kopya, boşa giden {F.human_size(g.wasted)}",
                                      F.human_size(g.size)])
            parent.setFirstColumnSpanned(False)
            for p in g.paths:
                child = QTreeWidgetItem([p, F.human_size(g.size)])
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Unchecked)
                child.setData(0, Qt.UserRole, p)
                parent.addChild(child)
            self.tree.addTopLevelItem(parent)
            parent.setExpanded(i <= 20)
        self.status.setText(
            f"{len(groups)} yinelenen grup bulundu. Kazanılabilecek alan: {F.human_size(wasted)}"
            if groups else "Yinelenen dosya bulunamadı. 🎉")
        self.trash_btn.setEnabled(bool(groups))
        self.select_btn.setEnabled(bool(groups))

    def _reveal(self, item, _col) -> None:
        p = item.data(0, Qt.UserRole)
        if p:
            show_in_explorer(p)

    def _check_all_but_first(self) -> None:
        for i in range(self.tree.topLevelItemCount()):
            g = self.tree.topLevelItem(i)
            for j in range(g.childCount()):
                g.child(j).setCheckState(0, Qt.Unchecked if j == 0 else Qt.Checked)

    def _trash_checked(self) -> None:
        selected: list[str] = []
        for i in range(self.tree.topLevelItemCount()):
            g = self.tree.topLevelItem(i)
            checked = [g.child(j) for j in range(g.childCount()) if g.child(j).checkState(0) == Qt.Checked]
            if checked and len(checked) == g.childCount():
                error(self, f"{g.text(0).split(' —')[0]} içindeki tüm kopyalar işaretli.\n"
                            "Veri kaybını önlemek için her grupta en az bir dosya bırakılmalıdır.")
                return
            selected += [c.data(0, Qt.UserRole) for c in checked]
        if not selected:
            info(self, "Önce taşınacak dosyaları işaretleyin.")
            return
        preview = "\n".join(selected[:10]) + ("\n…" if len(selected) > 10 else "")
        if not confirm(self, "Onay gerekli",
                       f"{len(selected)} dosya Geri Dönüşüm Kutusu'na taşınacak:\n\n{preview}\n\nDevam edilsin mi?",
                       danger=True):
            return
        try:
            from send2trash import send2trash
        except ImportError:
            error(self, "Geri Dönüşüm Kutusu desteği (send2trash) yüklü değil; işlem yapılmadı.")
            return
        ok, failed = 0, []
        for p in selected:
            try:
                send2trash(p)
                ok += 1
            except Exception as e:  # noqa: BLE001
                failed.append(f"{p}: {e}")
        msg = f"{ok} dosya Geri Dönüşüm Kutusu'na taşındı."
        if failed:
            msg += "\n\nTaşınamayanlar:\n" + "\n".join(failed[:10])
        info(self, msg)
        self.start()


class FolderTab(ScanTab):
    def __init__(self, main):
        super().__init__(main, "Klasörün toplam boyutunu, alt klasörlerin payını ve en büyük dosyaları gösterir.")
        self.summary = QLabel("")
        self.summary.setObjectName("CardTitle")
        self.lay.addWidget(self.summary)
        row = QHBoxLayout()
        self.child_table = make_table(["Öğe", "Boyut", "Pay", "Dosya"])
        self.largest = make_table(["En büyük dosyalar", "Boyut"])
        attach_path_menu(self.largest)
        row.addWidget(self.child_table, 1)
        row.addWidget(self.largest, 1)
        self.lay.addLayout(row, 1)

    def job(self, root):
        return lambda cancel, progress: F.analyze_folder(root, 100, cancel, progress)

    def show_result(self, rep: F.FolderReport) -> None:
        self.summary.setText(
            f"Toplam: {F.human_size(rep.total_size)}  •  {rep.file_count} dosya  •  {rep.folder_count} klasör")
        t = self.child_table
        t.setSortingEnabled(False)
        t.setRowCount(len(rep.children))
        for r, (name, size, count, is_dir) in enumerate(rep.children):
            item = QTableWidgetItem(("📁 " if is_dir else "📄 ") + name)
            item.setData(Qt.UserRole, os.path.join(rep.root, name))
            t.setItem(r, 0, item)
            t.setItem(r, 1, SizeItem(size))
            pct = (size / rep.total_size * 100) if rep.total_size else 0
            pi = QTableWidgetItem(f"%{pct:.1f}".replace(".", ","))
            pi.setData(Qt.UserRole, pct)
            t.setItem(r, 2, pi)
            t.setItem(r, 3, QTableWidgetItem(str(count)))
        t.setSortingEnabled(True)
        t2 = self.largest
        t2.setSortingEnabled(False)
        t2.setRowCount(len(rep.largest))
        for r, e in enumerate(rep.largest):
            item = QTableWidgetItem(e.path)
            item.setData(Qt.UserRole, e.path)
            t2.setItem(r, 0, item)
            t2.setItem(r, 1, SizeItem(e.size))
        t2.setSortingEnabled(True)
        self.status.setText("Analiz tamamlandı.")


class ExtensionTab(ScanTab):
    def __init__(self, main):
        super().__init__(main, "Dosya türlerinin sayısını ve kapladığı alanı uzantıya göre gruplar.")
        self.table = make_table(["Uzantı", "Toplam boyut", "Dosya sayısı", "Pay"])
        self.lay.addWidget(self.table, 1)

    def job(self, root):
        return lambda cancel, progress: F.extension_stats(root, cancel, progress)

    def show_result(self, stats) -> None:
        total = sum(s.total_size for s in stats) or 1
        t = self.table
        t.setSortingEnabled(False)
        t.setRowCount(len(stats))
        for r, s in enumerate(stats):
            t.setItem(r, 0, QTableWidgetItem(s.extension))
            t.setItem(r, 1, SizeItem(s.total_size))
            c = QTableWidgetItem()
            c.setData(Qt.DisplayRole, s.count)
            t.setItem(r, 2, c)
            t.setItem(r, 3, QTableWidgetItem(f"%{s.total_size / total * 100:.1f}".replace(".", ",")))
        t.setSortingEnabled(True)
        self.status.setText(f"{len(stats)} farklı uzantı bulundu.")


class FilesPage(QWidget):
    def __init__(self, main):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.addWidget(page_header("Dosya Araçları",
                                  "Arama, yinelenen dosya tespiti ve boyut analizleri. Dosyalarınız yalnızca okunur."))
        self.tabs = QTabWidget()
        self.search = SearchTab(main)
        self.dups = DuplicatesTab(main)
        self.folder = FolderTab(main)
        self.ext = ExtensionTab(main)
        self.tabs.addTab(self.search, "Dosya Arama")
        self.tabs.addTab(self.dups, "Yinelenen Dosyalar")
        self.tabs.addTab(self.folder, "Klasör / Boyut Analizi")
        self.tabs.addTab(self.ext, "Uzantı Analizi")
        lay.addWidget(self.tabs, 1)

    def open_tab(self, index: int) -> None:
        self.tabs.setCurrentIndex(index)

    def shutdown(self) -> None:
        for t in (self.search, self.dups, self.folder, self.ext):
            t.shutdown()
