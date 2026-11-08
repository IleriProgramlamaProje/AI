# veri_hazirlama/ (O1 · 2.4)
- `hazirla.py`: temiz veriyi karışım oranına göre birleştirir, `train.bin` / `val.bin` yazar (Git'e girmez, Drive'a konur).
  ```sh
  python ai/filtre/filtre.py ~/Downloads/kaydir_veri          # 1) ham → filtre/temiz
  python ai/veri_hazirlama/hazirla.py ~/Downloads/kaydir_veri # 2) filtre/temiz + altın set + hazır veri → egitim/
  ```
- **Karışım** (aralıkların ortası; `--oran ad=değer` ile değişir): öğretmen hikâyeleri %60 · öğretmen kartları %17,5 · altın set %5 · BİLGEM %10 · edebiyat %5.
  - Olmayan kaynağın payı diğerlerine oranla dağıtılır.
  - Toplam boyutu, oranına göre en kıt kaynak belirler. Belge tekrar edilmez; fazlası kullanılmaz ve raporda "kalan" sütununda görünür.
- **Val:** her kaynaktan %5, tekrar yok, train'den ayrı.
- **Kaynak yerleri:**
  - `<veri>/filtre/temiz/*.jsonl`: hikâye ve kart; kart `kart_bicimi.egitim_metni` ile etiketli metne çevrilir.
  - `data/altin_set/ham/*_egitim.txt`
  - `data/edebiyat/bilgem/*.txt` (BİLGEM) ve `data/edebiyat/` altındaki diğer `*.txt` dosyaları (edebiyat). Belgeler arasında boş satır olmalı.
- **Çıktı:** `<veri>/egitim/train.bin`, `val.bin`, `rapor.json` (kaynak başına belge ve token). Token biçimi: `ai/tokenizer/kodla.py` (uint16, belge sonunda `<|son|>`).
- **Test:** `ai/testler/test_hazirla.py`

8 Kasım (hazır veri yok, kelime kuralı açık): train 1.588.548 token, val 90.065 token. Gerçek oranlar hikâye %72,7, kart %21,2, altın set %6,1.
