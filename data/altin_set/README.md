# altin_set/

**11 Kasım:** Ekibin sohbet ekranlarında (Gemini, ChatGPT, Claude…) ürettiği altın set kartları depodan ve eğitim verisinden çıkarıldı. Bu servislerin kullanım şartları çıktıyla model eğitmeyi yasaklıyor ya da kısıtlıyor (`Docs/kararlar.md`). Eğitim verisinin tamamı Gemma 4 12B (Apache 2.0) üretimidir.

Bu klasör ileride şunlar için kullanılır:

| Dosya | Ne |
| --- | --- |
| `sinav.jsonl` | 200 kart. Temiz Gemma kartlarından seçilir, ekip okuyup düzeltir. **Modele hiç gösterilmez** |
| `yedek_deste.json` | Oyunun yedek destesi. Temiz Gemma kartlarından, ekip okuyarak seçer |

Biçim: `Docs/kart_formati.md` 3. bölüm (Godot JSON).
