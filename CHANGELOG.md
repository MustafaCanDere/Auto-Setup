# Değişiklik Günlüğü

## [3.4.0]
- **Canlı indirme ilerlemesi:** kurulum ekranı artık o an inen programın ne kadarının indiğini gösteriyor: yüzde, inen / toplam boyut, hız ve kalan süre (ör. `%42 · 120.3 MB / 286.0 MB · 8.3 MB/s · ~20 sn kaldı`). Ana çubuk da indirme boyunca akıcı ilerliyor.
- winget, pip (24.1+ ile `--progress-bar raw`, eskilerde dosya boyutu), git (`--progress`) ve doğrudan zip indirmelerinin hepsinde çalışır. Alttaki durum satırı ve çubuk da aynı bilgiyi gösterir.
- Konsol artık her ilerleme çubuğu karesiyle dolmuyor; yalnızca %25'lik adımlar yazılıyor.
- Testler: `tests/test_download_progress.py`.

## [3.3.0]
- **ArtCraft uygulamaları** (getartcraft.com/apps): ArtCraft Launcher kurulabilir olarak eklendi (Windows x64 portatif zip, v0.1.0) ve Tasarım profiline girdi. Launcher 13 uygulamanın hepsini kurar ve günceller.
- 13 uygulama için kart: PhotoCraft, VectorCraft, FilmCraft, LightCraft, PdfCraft, EffectCraft, DesignCraft, FigCraft, WordCraft, SoundCraft, DeckCraft, CADCraft, GridCraft. Uygulamalar erken alfada ve sık sürüm çıkardığı için kartlar GitHub'daki en güncel sürüm sayfasını açar.
- **Atolye.exe:** artık `.bat` yerine tek bir exe ile açılıyor, Python gerekmez. GitHub Actions her `main` push'unda exe'yi derler, açılıp açılmadığını dener ve Releases'e yükler. Seçimler exe'nin yanındaki `secilenler.json` dosyasına kaydedilir.
- Toplam 428 giriş (368 kurulabilir + 60 sayfa kartı).

## [3.2.0]
- İş yeri için genel araçlar: yeni **İş Yeri, İletişim & Ofis** kategorisi (tarayıcılar, Teams/Slack/Zoom, PDF, uzak erişim, disk ve sistem araçları, CapCut) ve **İş Yeri Paketi** profili.
- Her dalın gerçek iş dünyası araçları: eDrawings, DWG TrueView, Navisworks Freedom, JT2Go, EAGLE, AnyLogic, Minitab ve daha fazlası winget ile kurulur.
- Yeni `web` türü: 47 ticari yazılım (SolidWorks, AutoCAD, Revit, MATLAB, ANSYS, TIA Portal, Altium...) için resmî sayfa kartı. Tıklayınca sayfa açılır, hiçbir şey indirilmez. Profillere ve toplu seçime girmez.
- Toplam 414 girişe ulaşıldı (367 kurulabilir + 47 resmî sayfa).
- **Hız:** kartlar tek çizim alanına taşındı. Kategori geçişi 1,8 sn'den 0,2 sn'ye, açılış 3,5 sn'den ~2 sn'ye düştü. Toplu seçimlerde dosya her program için değil tek seferde kaydediliyor.
- **Düzeltme:** sağ taraftaki program listesi fare tekerleğiyle kaydırılamıyordu (sol panelle yol adı çakışması).
- Entegrasyon testi eklendi (varsayılan olarak atlanır): `tests/test_engine_integration.py`.

## [3.1.0]
- Her mühendislik dalına özel niş araçlar: 6 yeni kategori ve 53 yeni program (toplam 275). Winget kimlikleri ve pip paket adları eklenmeden önce tek tek doğrulandı.
- 6 yeni hazır profil (Makine, Elektrik-Elektronik, İnşaat & Harita, Kimya & Biyo, Uzay & Endüstri, Matematik & Bilim).
- Yeni yükleme ekranı: dönen simge, yumuşak dolan ilerleme çubuğu, canlı sayaçlar, bitiş özeti.
- Özel yuvarlak onay kutuları.
- Sol panel kaydırılabilir oldu.
- Köşe çizimi daha yuvarlak ve net.

## [3.0.0]
- Proje adı **Atölye** oldu.
- Apple tarzı açık tema, sade başlık, arama kutusunda yer tutucu metin.
- Yumuşak görünüm: yuvarlak köşeli kartlar, düğmeler, arama alanı ve istatistik kutusu; neredeyse görünmez kenarlıklar.
- Kartın her yerine tıklayarak seçme, hover efektleri, koyu kaydırma çubuğu.
- Hazır profiller 2 sütunlu ızgaraya taşındı, alt istatistik kutusu kesilmiyor.
- Git klonlamada `core.longpaths` açıldı (Windows uzun yol hatası düzeltildi).
- Zip açarken zip-slip koruması eklendi.
- 32-bit Python için uyarı eklendi.
- Veritabanı testleri ve GitHub Actions CI eklendi.
- Tanıtım sayfası (`docs/index.html`) eklendi.

## [2.6.0]
- İlk sürüm: 222 araç, 9 kategori, hazır profiller.
