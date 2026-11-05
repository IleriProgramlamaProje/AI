# Altın set

| Dosya | Ne |
| --- | --- |
| `ham/` | Sayfanın Veri sekmesinden indirilen dosyalar (`altin_set_ham*.jsonl`, `altin_set*.json`) |
| `sinav.jsonl` | 200 kart (4. hafta). **Modele hiç gösterilmez** |
| `yedek_deste.json` | En iyi kartlar (hedef 600). Godot'ye kopyalanır |

- Biçim: `docs/kart_formati.md` 3. bölüm (Godot JSON), `"kaynak": "altin_set"`, `"lisans": "sadece_ders"`.
- Hız: 10–100 kartlık paketlerle kişi başı günde 1000+ kart hedeflenir (2 Kasım).
- Kartlar `ai/altin_set/` sayfasında üretilir; 2 Kasım'dan beri okuma yok, kurallar otomatik kontrol edilir. Sayfanın Veri sekmesinden indirilen dosyalar buraya konur.

**3 Kasım:** ekipten gelen düz metin (20 kadar paket, 1.626 kart) sayfanın kendi ayrıştırıcı ve kontrolüyle çevrildi → `ham/altin_set.json`, `ham/altin_set_ham.jsonl`, `ham/altin_set_egitim.txt`. **1.448 kart geçti** (103'ü uyarılı), 178'i atıldı: 86'sında kelime yok, 48'inin malzeme satırı kaynakta bozuk, 23'ünde modern kelime var, 11'inde hitap elle yazılmış, gerisi etki ya da eksik satır hatası. Kaynakta model bilgisi olmadığı için `model: bilinmiyor`.
