# Torbalar · 25 Ekim 2026

**Asıl kaynak:** Ekibin Drive'daki `Torba_Listesi` tablosu. Buradakiler kodun okuduğu dışa aktarımlar.

| Dosya | Sayı | Biçim / not |
| --- | --- | --- |
| `kelimeler.csv` | **2000** (733 isim · 640 fiil · 627 sıfat) | kelime, tur, ekleyen |
| `karakterler.csv` | **23 rol** (Yönetim 7 · Ordu 4 · Halk 6 · Para 6) | rol, ton, gorev, ornek, alan, cinsiyet, sik_sozler, asla, farki (kimlik kartı). Örneklerde hitap `{hitap}` |
| `olaylar.csv` | **200** (her alanda 50) | id, olay, alan, etiket, sol_secenek, sol_etki, sag_secenek, sag_etki (onaylı etkiler, model biçiminde: `<para-> <halk+>`) |
| `Olay_Etkileri_Oneri.xlsx` | 200 | Eski ve yeni etkiler yan yana (onaylandı, arşiv) |
| `konular.txt` | 100 | her satırda bir konu |
| `yer.txt` | 60 | |
| `usluplar.txt` | 60 | Gemma'nın iyi taklit edemediği üsluplar denemeden sonra çıkarılacak |
| `ikilem.csv` | 60 | taraf1, taraf2 |
| `ozellikler.txt`, `ruh_hali.txt`, `zaman.txt` | 40'ar | |

Kurallar: `docs/hazirlik_haftasi.md` 2. bölüm.
