# Altın set

| Dosya | Ne |
| --- | --- |
| `ham/` | Sayfanın Veri sekmesinden indirilen dosyalar (`altin_set_ham*.jsonl`, `altin_set*.json`) |
| `sinav.jsonl` | 200 kart (4. hafta). **Modele hiç gösterilmez** |
| `yedek_deste.json` | En iyi kartlar (hedef 600). Godot'ye kopyalanır |

- Biçim: `docs/kart_formati.md` 3. bölüm (Godot JSON), `"kaynak": "altin_set"`, `"lisans": "sadece_ders"`.
- Hız: 10–100 kartlık paketlerle kişi başı günde 1000+ kart hedeflenir (2 Kasım).
- Kartlar `ai/altin_set/` sayfasında üretilir; 2 Kasım'dan beri okuma yok, kurallar otomatik kontrol edilir. Sayfanın Veri sekmesinden indirilen dosyalar buraya konur.
