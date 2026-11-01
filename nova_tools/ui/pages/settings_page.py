"""Ayarlar: tema, dil, veritabanı yedekleme/geri yükleme."""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtWidgets import (
    QButtonGroup, QFileDialog, QHBoxLayout, QLabel, QPushButton, QRadioButton, QVBoxLayout, QWidget,
)

from ... import APP_NAME, __version__
from ...core.storage import Storage, is_portable
from ..widgets import Card, confirm, error, info, muted_label, open_path, page_header, primary_button, scroll_page


class SettingsPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        lay.addWidget(page_header("Ayarlar", "Görünüm, dil ve veri yönetimi."))

        theme = Card("Tema")
        row = QHBoxLayout()
        self.dark = QRadioButton("🌙  Koyu")
        self.light = QRadioButton("☀️  Açık")
        grp = QButtonGroup(self)
        grp.addButton(self.dark)
        grp.addButton(self.light)
        (self.light if main.theme_mode == "light" else self.dark).setChecked(True)
        self.dark.toggled.connect(lambda on: on and self.main.apply_theme("dark"))
        self.light.toggled.connect(lambda on: on and self.main.apply_theme("light"))
        row.addWidget(self.dark)
        row.addWidget(self.light)
        row.addStretch(1)
        theme.body.addLayout(row)
        lay.addWidget(theme)

        lang = Card("Dil")
        lang.body.addWidget(QLabel("Arayüz dili: Türkçe"))
        lang.body.addWidget(muted_label("Tüm menüler, mesajlar ve biçimler Türkçedir."))
        lay.addWidget(lang)

        data = Card("Veritabanı")
        self.path_lbl = muted_label()
        data.body.addWidget(self.path_lbl)
        mode = "Taşınabilir mod (veriler program klasöründe)" if is_portable() else "Standart mod (veriler kullanıcı profilinde)"
        data.body.addWidget(muted_label(mode))
        b = QHBoxLayout()
        backup = primary_button("Yedekle…")
        restore = QPushButton("Yedekten geri yükle…")
        open_dir = QPushButton("Veri klasörünü aç")
        backup.clicked.connect(self.backup)
        restore.clicked.connect(self.restore)
        open_dir.clicked.connect(lambda: open_path(os.path.dirname(self.main.storage.path)))
        for w in (backup, restore, open_dir):
            b.addWidget(w)
        b.addStretch(1)
        data.body.addLayout(b)
        data.body.addWidget(muted_label("Yedek; notları, ayarları, dünya saatlerini ve son kullanılan araçları içerir."))
        lay.addWidget(data)

        about = Card("Hakkında")
        about.body.addWidget(QLabel(f"{APP_NAME} {__version__}"))
        about.body.addWidget(muted_label(
            "Tamamen çevrimdışı çalışır; internet bağlantısı, hesap veya yönetici izni gerektirmez. "
            "Dosyalar kullanıcı onayı olmadan değiştirilmez veya silinmez."))
        lay.addWidget(about)
        lay.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll_page(content))
        self.on_show()

    def on_show(self) -> None:
        self.path_lbl.setText(f"Konum: {self.main.storage.path}")

    def backup(self) -> None:
        name = f"nova_tools_yedek_{datetime.now():%Y%m%d_%H%M}.db"
        path, _ = QFileDialog.getSaveFileName(self, "Yedeği kaydet", os.path.join(os.path.expanduser("~"), name),
                                              "Nova Tools yedeği (*.db)")
        if not path:
            return
        try:
            self.main.pages["notes"].save_current()
            self.main.storage.backup_to(path)
        except (OSError, ValueError, Exception) as e:  # noqa: BLE001
            error(self, f"Yedekleme başarısız:\n{e}")
            return
        info(self, f"Yedek oluşturuldu:\n{path}")

    def restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Yedek seç", os.path.expanduser("~"), "Nova Tools yedeği (*.db);;Tüm dosyalar (*)")
        if not path:
            return
        try:
            count = Storage.validate_backup(path)
        except ValueError as e:
            error(self, str(e))
            return
        if not confirm(self, "Geri yükleme onayı",
                       f"Yedekte {count} not var.\nMevcut tüm veriler yedektekilerle değiştirilecek. Devam edilsin mi?",
                       danger=True):
            return
        try:
            self.main.storage.restore_from(path)
        except Exception as e:  # noqa: BLE001
            error(self, f"Geri yükleme başarısız:\n{e}")
            return
        notes = self.main.pages["notes"]
        notes.current_id = None
        notes.on_show()
        self.main.apply_theme(self.main.storage.get("theme", "dark"), save=False)
        (self.light if self.main.theme_mode == "light" else self.dark).setChecked(True)
        info(self, "Yedek geri yüklendi. Dünya saatleri listesi bir sonraki açılışta güncellenir.")
