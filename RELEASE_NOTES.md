## Nova Tools – Windows 10/11 masaüstü araç kutusu

Dosya arama, yinelenen dosya tespiti, klasör/uzantı analizi, metin editörü ve sayaçlar, metin karşılaştırma, JSON, Base64,
bilimsel hesap makinesi, birim dönüştürücü, SHA-256, kronometre, geri sayım, Pomodoro, dünya saatleri ve otomatik kaydedilen notlar.
Tamamen çevrimdışı; yönetici izni istemez.

| Dosya | Açıklama |
|---|---|
| `NovaTools-vX.Y.Z.exe` | Tek dosya, kurulum gerektirmez. Veriler `%APPDATA%\NovaTools` içinde. |
| `NovaTools-vX.Y.Z-Portable.zip` | Taşınabilir sürüm: açın, `NovaTools\NovaTools.exe` çalıştırın. Veriler program klasöründeki `data\` altında. |
| `SHA256SUMS.txt` | Dosya doğrulama özetleri |

**Kod imzası:** EXE dosyaları imzalı değildir (kod imzalama sertifikası mevcut değil). Windows SmartScreen uyarısında
**Ek bilgi → Yine de çalıştır** seçin; dosyayı `SHA256SUMS.txt` ile doğrulayabilirsiniz.

### Doğrulama
- 53 çekirdek testi + ekransız arayüz testi (Windows runner)
- Derlenen **her iki EXE de** `--self-test` ile gerçekten açılıp 11 kontrolden geçirildi
