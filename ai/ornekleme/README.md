# ornekleme/

`ornek_uret.py`: eğitilmiş modelden hikâye ya da kart üretir.

```bash
# 100 kart: rastgele durum satırı + konuşan verilir, model gövdeyi </kart>'a kadar yazar
python ai/ornekleme/ornek_uret.py --model modeller/1m/en_iyi.pt --tokenizer egitim/tokenizer.json \
    --tur kart --adet 100 --sicaklik 0.8 --cikti ornek_kartlar.jsonl
# hikâye
python ai/ornekleme/ornek_uret.py --model ... --tokenizer ... --tur hikaye --adet 3 --baslangic "Bir gün"
```

Kart modunda sonda iki oran yazar:
- **biçim geçerli**: `kart_bicimi.metinden_karta` okuyabildi mi (etiketler yerinde, etkiler geçerli). Oyun bozuk kartı atar, yedek desteden çeker.
- **içerik de geçerli**: her seçenekte 1–3 etki ve en az bir düşüş var mı.

Ayarlar: `--sicaklik` (0,7–0,9 denenecek; düşük = tekdüze, yüksek = hatalı), `--top-k` (varsayılan 50), `--uzunluk` (en fazla yeni token), `--konusan hazinedar` (sabit karakter), `--tohum`.
