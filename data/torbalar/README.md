# Torbalar

| Dosya | Sayı | Sütunlar |
| --- | --- | --- |
| `kelimeler.csv` | 1500 (613 isim · 475 fiil · 412 sıfat) | kelime, tur |
| `karakterler.csv` | 23 rol (Yönetim 7 · Ordu 4 · Halk 6 · Para 6) | rol, ton, gorev, ornek, alan, cinsiyet, sik_sozler, asla, farki |
| `olaylar.csv` | 200 (her alanda 50) | id, olay, alan, etiket, sol_secenek, sol_etki, sag_secenek, sag_etki |
| `konular.txt` | 100 | her satırda bir konu |
| `yer.txt` | 60 | her satırda bir yer |
| `usluplar.txt` | 60 | her satırda bir üslup |
| `ikilem.csv` | 60 | taraf1, taraf2 |
| `ozellikler.txt` | 40 | her satırda bir özellik |
| `ruh_hali.txt` | 40 | her satırda bir ruh hâli |
| `zaman.txt` | 40 | her satırda bir zaman |

`Docs/tema.json` (kardeş depo): göstergeler, etki kademeleri, sonlar, karakter kimlikleri, yasak kelimeler.

Kullanım (1 Kasım kararı): hikâyede karakter + 3 kelime (1 isim, 1 fiil, 1 sıfat), kartta karakter + 2 kelime (1 isim, 1 sıfat); diğer torbalardan rastgele 1–2. Kodda henüz 3 rastgele kelime çekiliyor; türe göre çekme görev M1 (Docs/yz_gorevleri.md).
