# model/

| Dosya | Ne yapar |
|---|---|
| `model.py` | Küçük GPT (nanoGPT örnek alınarak, Türkçe açıklamalı): gömme → `katman` × (dikkat + MLP) → çıkış. `uret()` sıcaklık, top-k ve durma token'ıyla metin üretir |
| `boyutlar/1m.yaml` | 4 katman · 4 kafa · genişlik 96 · ~1,2M parametre |
| `boyutlar/10m.yaml` | 6 katman · 5 kafa · genişlik 320 · ~10M parametre |
| `boyutlar/30m.yaml` | 8 katman · 8 kafa · genişlik 512 · ~30M parametre |

yaml'larda model ayarlarının yanında eğitim ayarları da var (`ogrenme_orani`, `yigin`, `tur`); `Ayar.sozlukten` bilmediği anahtarları atlar.
Bağlam hepsinde 256 token: bir kart ~96, bir hikâye ~144 token, ikisi de rahat sığar. Sözlük boyutu eğitimde `tokenizer.json`'dan okunur (yaml'daki 8000 yedek).

Neden bu üç boyut, ne kadar veri ister (Chinchilla: parametre başına ~20 token, en fazla 4 tur): 1M ≈ 5–20M token · 10M ≈ 50–200M · 30M ≈ 150–600M.
Elimizdeki veri azsa büyük model ezberler: `egit.py` val kaybı iyileşmeyince durur, en iyi nokta `en_iyi.pt`'de kalır. Karar ~2 Aralık'ta üç modelin val kaybı ve geçerli kart oranıyla verilir.

Test: `python -m pytest ai/testler/test_model.py` (CPU, birkaç saniye; parametre sayıları da burada kontrol edilir).
