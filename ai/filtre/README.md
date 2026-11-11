# filtre/
- `filtre.py` (S1): ham üretimi filtreler, hangi kuraldan kaç kaydın atıldığını raporlar.
  `python ai/filtre/filtre.py <veri klasörü>` → `<veri>/filtre/temiz/`, `elenen/`, `rapor.md`, `rapor.json`.
  - Biçim çözme, sınırlar ve prompt kuralları `duzenle.py` ile ortaktır.
  - Bunlara ek olarak boş çıktıyı, bozuk kelimeyi (ünlü uyumu), modern kelimeyi ve verilen kelimeleri kontrol eder.
  - Kartta `kart` alanı S2'nin (`kart_bicimi.py`) okuduğu sözlüktür.
  - `--kelimeye-bakma` verilen kelime kuralını kapatır. Kural açıkken kartların yaklaşık yarısı bu yüzden elenir (8 Kasım verisi: kart %51 / %92, hikâye %69 / %89).
  - Test: `ai/testler/test_filtre.py`
- `duzenle.py`: 7 Kasım'a kadarki temiz verinin geçtiği temizlik. `python ai/filtre/duzenle.py <veri klasörü>` komutuyla çalışır.
  - `ham/` (ve varsa eski `altin/`) okur; `temiz/` ve `silindi/` yazar. Girdileri değiştirmez. Altın set 11 Kasım'da çıkarıldı, `altin/` klasörü yoksa o kısım atlanır.
  - Test: `ai/testler/test_duzenle.py`

Sınırlar ve açık kararlar: `kararlar.md` 7 Kasım. Hangi betiğin esas olacağı ve verilen kelime kuralı toplantıda kesinleşir.
