# Değişiklik Günlüğü

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
