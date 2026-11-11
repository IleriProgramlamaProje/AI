# egitim/

| Dosya | Ne yapar |
|---|---|
| `egit.py` | Ön eğitim döngüsü: `train.bin`'den rastgele 256 token'lık parçalar, AdamW, ısınma + kosinüs öğrenme oranı, GPU'da fp16. Her `--olcum-araligi` adımda train/val kaybı → `kayip.csv`; en iyi val → `en_iyi.pt`, her ölçümde `son.pt`. Val `--sabir` ölçüm iyileşmezse durur. Sonunda `kayip.png` |
| `egitim.ipynb` | Colab ve Kaggle defteri: depoyu indirir, veriyi Drive'dan / Kaggle Dataset'ten bulur, `egit.py`'yi çalıştırır, grafiği ve 100 örnek kartın geçerlilik oranını gösterir |
| `ince_ayar.py` [H5] | ince ayar: en iyi temiz Gemma kartlarıyla · 1. tur ~1.250 kart · 2. tur ~2.300 kart |

## Çalıştırma
Önce üç dosya tek klasörde olmalı: `train.bin`, `val.bin` (`hazirla.py` çıktısı) ve `tokenizer.json` (**aynı** tokenizer; farklıysa `egit.py` hata verir).

```bash
python ai/egitim/egit.py --boyut ai/model/boyutlar/1m.yaml --veri ~/kaydir_veri/egitim \
    --tokenizer ~/kaydir_veri/egitim/tokenizer.json --cikti ~/kaydir_veri/modeller/1m
# hızlı deneme: --adim 300 · koptuysa aynı komut + --devam · bellek yetmezse --yigin 16 --biriktir 2
```

Çıktı klasörü: `en_iyi.pt` (oyuna/ince ayara giden), `son.pt` (devam için), `kayip.csv`, `kayip.png`, `ayar.json`.

## Kayıp nasıl okunur
- Başlangıç ~ln(8000) ≈ 9. Hızla 4–5'e iner, sonra yavaşlar.
- Train ve val birlikte iniyorsa model öğreniyor. Train inip val çıkıyorsa ezber: daha çok veri ya da daha küçük model.
- Üç boyut karşılaştırılırken aynı `val.bin` kullanılmalı; yoksa sayılar karşılaştırılamaz.
