# Altın set

| Dosya | Ne |
| --- | --- |
| `ham/` | Sohbet ekranından gelen, henüz okunmamış kartlar (kişi başına bir dosya önerilir: `ham/mert.jsonl`) |
| `iyi.jsonl` | Çapraz okumadan "iyi" alanlar |
| `sinav.jsonl` | 200 kart (4. hafta). **Modele hiç gösterilmez** |
| `yedek_deste.json` | En iyi kartlar (hedef 600). Unity'ye kopyalanır |

- Biçim: `docs/kart_formati.md` 3. bölüm (Unity JSON), `"kaynak": "altin_set"`, `"lisans": "sadece_ders"`.
- Hız: haftada ~310 iyi kart, kişi başı günde ~11.
- Okuma sırası: Mert → Sokul'un · Sokul → Kara'nın · Kara → Muhammet'in · Muhammet → Mert'in.
