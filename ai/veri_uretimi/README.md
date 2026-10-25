# veri_uretimi/ · hazır ✓

**Hızlı başlangıç (Colab):** `hiz_olcumu.ipynb` → sonra her gece `uretim.ipynb`. Öğretmen: `google/gemma-4-E4B-it` (Hugging Face'te lisansı kabul et).
Kural: karakter + 3 kelime her zaman; diğer torbalardan rastgele 1-2; kartların ~%15'inde konu serbest.

- `torbalar.py` [Hz]: torbaları okur, rastgele çeker
- `istek_olusturucu.py` [Hz]: torbadan öğretmen promptu kurar (hikâye / kart)
- `uretici.py` [Hz]: öğretmen modeli çalıştırır, çıktıyı dosyaya yazar
- `promptlar/hikaye.txt`, `uslup.txt` [Hz] · `promptlar/kart.txt` [H1, yeni kart biçimine göre]
- `hiz_olcumu.ipynb` [Hz]: Colab, Gemma 4 / Qwen 3.5 saatte kaç hikâye
- `uretim.ipynb` [H1]: Colab, gece boyu toplu üretim (o dönemin YZ ekibi kendi hesaplarıyla)

Model denemesinde kullanılan promptlar: `docs/raporlar/ogretmen_secimi.md` 2. bölüm.
