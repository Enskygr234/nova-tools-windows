# Nova Tools – Windows Masaüstü Araç Kutusu

[![Windows Build](https://github.com/Enskygr234/nova-tools-windows/actions/workflows/windows.yml/badge.svg)](https://github.com/Enskygr234/nova-tools-windows/actions/workflows/windows.yml)

Günlük bilgisayar işlerini tek pencerede toplayan, **tamamen çevrimdışı**, Türkçe arayüzlü,
modern bir Windows 10/11 uygulaması. İnternet, hesap, ücretli API veya yönetici izni gerektirmez.

## İndir

**[Son sürüm → Releases](https://github.com/Enskygr234/nova-tools-windows/releases/latest)**

| Dosya | Açıklama |
|---|---|
| `NovaTools-vX.Y.Z.exe` | Tek dosya; çift tıklayıp çalıştırın. Veriler `%APPDATA%\NovaTools` içinde saklanır. |
| `NovaTools-vX.Y.Z-Portable.zip` | Taşınabilir sürüm; zip'i açıp `NovaTools\NovaTools.exe` çalıştırın. Veriler program klasöründeki `data\` altında kalır (USB bellekte taşınabilir). |
| `SHA256SUMS.txt` | Dosya doğrulama özetleri (uygulamanın kendi SHA-256 aracıyla kontrol edebilirsiniz). |

> **Kod imzası hakkında:** EXE dosyaları bir kod imzalama sertifikasıyla **imzalanmamıştır** (sertifika mevcut değil).
> Bu nedenle Windows SmartScreen ilk çalıştırmada "Windows bilgisayarınızı korudu" uyarısı gösterebilir:
> **Ek bilgi → Yine de çalıştır** ile açabilirsiniz. Dosyanın bütünlüğünü `SHA256SUMS.txt` ile doğrulayabilirsiniz.

## Özellikler

| Bölüm | Araçlar |
|---|---|
| 🏠 **Ana Sayfa** | Selamlama ve tarih, 12 hızlı erişim kartı, son kullanılan araçlar (kullanım sayısıyla), not sayısı, canlı saat |
| 📁 **Dosya Araçları** | Dosya arama (ad / joker / çoklu desen, uzantı, en küçük boyut), yinelenen dosya tespiti (boyut → kısmi özet → tam SHA-256), klasör ve boyut analizi (alt öğe payları + en büyük 100 dosya), uzantı analizi |
| 📝 **Metin Araçları** | Metin editörü (aç/kaydet/farklı kaydet, UTF-8/Windows-1254 algılama, kaydedilmemiş değişiklik uyarısı), kelime ve karakter sayacı (cümle, paragraf, okuma süresi, en sık kelimeler), metin karşılaştırma (renkli fark, benzerlik oranı), JSON biçimlendirme/küçültme/doğrulama, Base64 kodlama-çözme (URL-güvenli seçeneği) |
| 🧮 **Hesaplama** | Bilimsel hesap makinesi (trigonometri DEG/RAD, log, ln, kök, üs, faktöriyel, yüzde, geçmiş, Ans), birim dönüştürücü (10 kategori: uzunluk, ağırlık, alan, hacim, hız, zaman, veri, basınç, enerji, sıcaklık), SHA-256 (metin ve dosya, beklenen özetle karşılaştırma) |
| ⏱️ **Zaman Araçları** | Kronometre (tur), geri sayım (hazır süreler, sesli + sistem bildirimi), Pomodoro (ayarlanabilir süreler, uzun mola döngüsü), dünya saatleri (eklenebilir/kaldırılabilir, kalıcı) |
| 🗒️ **Notlar** | Hızlı notlar, kategoriler (yeni kategori yazılabilir), Türkçe karakter duyarlı arama, **otomatik kaydetme** |
| ⚙️ **Ayarlar** | Koyu/açık tema, Türkçe dil, veritabanı yedekleme ve geri yükleme (doğrulamalı), veri klasörünü açma |

**Tasarım:** sol navigasyon menüsü (Ctrl+1…7 kısayolları), mor-mavi degrade vurgular, kart tabanlı düzen,
sayfa geçişlerinde yumuşak solma animasyonu, pencere boyutuna göre yeniden düzenlenen ana sayfa ızgarası.

## Güvenlik ilkeleri

- **Hiçbir dosya kullanıcı onayı olmadan silinmez veya değiştirilmez.** Dosya analiz araçları yalnızca okur.
- Yinelenen dosyalar yalnızca kullanıcı işaretleyip onayladığında, kalıcı silme yerine **Geri Dönüşüm Kutusu'na** taşınır;
  bir gruptaki tüm kopyaların seçilmesi engellenir.
- Editörde var olan bir dosyanın üzerine yazmadan önce Windows kaydetme penceresi onay ister; kaydedilmemiş değişiklikler için uyarı verilir.
- Hesap makinesi `eval()` kullanmaz; ifadeler güvenli bir AST değerlendiricisiyle hesaplanır (aşırı büyük üs/faktöriyel engellenir).
- Uzun işlemler arka plan iş parçacığında çalışır ve **Durdur** ile iptal edilebilir; erişilemeyen klasörler atlanır, hatalar arayüzü çökertmez.
- Yönetici izni istenmez (`asInvoker`).

## Kaynaktan çalıştırma

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Python 3.10+ gerekir.

## Test

```powershell
pip install -r requirements-dev.txt
python -m pytest -v
```

- `tests/test_core.py` – dosya araçları, yinelenen tespiti, metin/JSON/Base64, hesap makinesi güvenliği, birimler, Pomodoro, saat dilimleri, SQLite depolama ve yedekleme (53 test)
- `tests/test_ui.py` – uygulamayı ekransız açar; tüm sayfa ve sekmeleri gezer, hesap makinesi, dönüştürücü, SHA-256, metin araçları, notlar, arka plan dosya araması, zaman araçları, tema ve yedeklemeyi dener

Derlenmiş EXE de aynı kontrolü kendi üzerinde çalıştırabilir:

```powershell
NovaTools.exe --self-test=rapor.json   # çıkış kodu 0 = tüm kontroller başarılı
```

## EXE derleme

```powershell
pip install -r requirements-dev.txt
pyinstaller --noconfirm --onefile --windowed --name NovaTools --icon assets/icon.ico `
  --add-data "assets;assets" --collect-data tzdata --version-file version_info.txt run.py
```

## GitHub Actions

`.github/workflows/windows.yml` her push'ta Windows runner üzerinde:

1. Tüm testleri çalıştırır
2. Tek dosya EXE ve taşınabilir sürümü PyInstaller ile derler
3. **Derlenen EXE'leri `--self-test` ile gerçekten açıp doğrular**
4. EXE, Portable.zip ve SHA256SUMS dosyalarını artifact olarak yükler
5. `v*` etiketiyle push edildiğinde bunları GitHub Releases'e ekler

## Proje yapısı

```
nova_tools/
├── core/          Saf Python mantığı (arayüzden bağımsız, test edilir)
│   ├── files.py   arama, yinelenenler, klasör/uzantı analizi
│   ├── text.py    sayaçlar, fark, JSON, Base64
│   ├── calc.py    güvenli hesap makinesi, SHA-256
│   ├── units.py   birim dönüştürücü
│   ├── timeutil.py Pomodoro, dünya saatleri
│   └── storage.py SQLite (notlar, ayarlar, son kullanılanlar, yedek)
├── ui/            PySide6 arayüzü (tema, bileşenler, sayfalar)
├── selftest.py    kendi kendini doğrulama
└── main.py        giriş noktası
```

## Lisans

MIT – bkz. [LICENSE](LICENSE).
