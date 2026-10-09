# ⚡ Mühendis Süper Kurulum Merkezi

Mühendisler ve geliştiriciler için **tik tik** seçmeli, Windows'ta tek tıkla çalışan kurulum paketi. İstediğin programları işaretle, **Seçilenleri Kur** butonuna bas, gerisini o halletsin.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Özellikler

- **Harici bağımlılık yok:** Sadece standart Python (Tkinter) kullanır.
- **222+ araç**, kategorilere ayrılmış: yapay zeka, yazılım, donanım/gömülü, DevOps, tasarım, ofis ve daha fazlası.
- **Hazır profiller:** Yapay Zeka, Full-Stack, Donanım & IoT, DevOps, Tasarım & 3D ve diğerleri.
- **Canlı arama ve kategori filtresi.**
- **GitHub projeleri:** Seçtiğin açık kaynak projeleri klonlar, `requirements.txt` kurar, tek tıkla başlatıcı `.bat` oluşturur.
- **Seçimlerini hatırlar** (`secilenler.json`).
- **Sırayla, kararlı kurulum:** İlerleme çubuğu ve canlı terminal çıktısı.

## 🚀 Hızlı Başlangıç

1. Bu repoyu indir (`Code → Download ZIP`) veya klonla:
   ```bash
   git clone https://github.com/<kullanici-adin>/muhendis-kurulum.git
   ```
2. `KURULUM_BASLAT.bat` dosyasına çift tıkla. Python yoksa Winget ile kurulmasını önerir.
3. Kurmak istediğin programları işaretle (veya soldan hazır profil seç).
4. **🚀 SEÇİLENLERİ KUR** butonuna bas.

## 📋 Gereksinimler

- Windows 10/11
- [Winget](https://learn.microsoft.com/windows/package-manager/) (Windows 11'de hazır gelir)
- İnternet bağlantısı

## 📁 Dosyalar

| Dosya | Görev |
|---|---|
| `muhendis_kurulum.py` | Arayüz ve kurulum motoru |
| `programlar_db.py` | Program, kategori ve profil veritabanı |
| `baslat.bat` / `KURULUM_BASLAT.bat` | Başlatıcılar |

## ➕ Program Ekleme

`programlar_db.py` içindeki `PROGRAMS` listesine yeni bir kayıt ekle, uygulama bir sonraki açılışta onu gösterir.

## ⚠️ Sorumluluk Reddi

Listede siber güvenlik ve pentest araçları da bulunur. Bunları **sadece kendi sistemlerinde veya yazılı izin aldığın ortamlarda** kullan. Kurulan her programın lisansı kendi sahibine aittir. Bu proje programların kendisini dağıtmaz, resmî kaynaklardan (Winget, pip, GitHub) kurar.

## 📄 Lisans

MIT, bkz. [LICENSE](LICENSE).
