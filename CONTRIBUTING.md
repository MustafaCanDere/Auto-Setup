# Katkı Rehberi

Atölye'ye katkıda bulunduğun için teşekkürler.

## Yeni program ekleme

`programlar_db.py` içindeki `PROGRAMS` listesine bir kayıt ekle:

```python
{
    "id": "ornek_arac",            # benzersiz, küçük harf ve alt çizgi
    "name": "Örnek Araç",
    "category": "dev",             # CATEGORIES içindeki id'lerden biri
    "type": "winget",              # winget | pip | git_repo | direct_zip | direct_exe
    "package_id": "Yayinci.OrnekArac",
    "desc": "Bir cümlelik Türkçe açıklama",
    "tags": ["ornek", "arac"],
    "default": False,
}
```

Kurallar:
- `git_repo` ve `direct_zip` adresleri **https** olmalı.
- Sadece resmî veya iyi bilinen kaynaklardan ekle. Zararlı veya lisansı belirsiz proje ekleme.
- Yeni programı uygun bir profile (`PRESETS`) eklemek istersen `ids` listesine yaz.

## Çalıştırma ve test

```bash
python atolye.py                    # arayüzü aç
python -m unittest discover -s tests -v   # testleri çalıştır
```

Pull request açmadan önce testlerin geçtiğinden emin ol. CI aynı testleri Windows ve Linux'ta çalıştırır.

## Arayüz değişiklikleri

Renkler `atolye.py` içindeki `THEME` sözlüğündedir. Yeni renk eklemek yerine mevcut olanları kullan, mümkünse değişikliğin ekran görüntüsünü PR'a ekle.
