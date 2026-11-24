# Edebiyat kaynakları

| Dosya | Eser | Kelime | Token | Kaynak | Lisans |
| --- | --- | --- | --- | --- | --- |
| `omer_seyfettin.txt` | 73 hikâye | 114.786 | ~277 bin | [Vikikaynak · Kişi:Ömer Seyfettin](https://tr.wikisource.org/wiki/Ki%C5%9Fi:%C3%96mer_Seyfettin) | Kamu malı (yazar 1920'de öldü) |
| `nasreddin_hoca.txt` | 165 fıkra | 12.574 | ~28 bin | [Vikikaynak · Nasreddin Hoca](https://tr.wikisource.org/w/index.php?search=Nasreddin+Hoca&fulltext=1) | Vikikaynak'ta "anonim eser, kamu malı" olarak işaretli |
| `bilgem/bilgem.txt` | 4.217 hikâye | 1.500.286 | ~3,1 milyon | bkz. `bilgem/KAYNAK.md` | Apache 2.0 |

Üreten: `python ai/veri_hazirlama/vikikaynak_temizle.py <vikikaynak_hikayeler klasörü>` (Vikikaynak sayfaları elle .txt olarak indirildi, 24 Kasım 2026).
Token sayıları `ai/tokenizer/cikti/tokenizer.json` ile.

## Notlar

- **Nasreddin Hoca:** Fıkraların çoğu Vikikaynak'ta Bayraktar, Z. (2010), *Mizah teorileri ve mizah teorilerine göre Nasreddin Hoca fıkralarının tahlili* (doktora tezi, Ege Üniversitesi) kaynağıyla girilmiş. Fıkralar anonim, ama metinlerin bu tezdeki anlatımı olabilir; Vikikaynak'ın "anonim" etiketine güveniyoruz.
- **Atılanlar:** "Aklı Yoktu ki" (eski dilde manzum fıkra).
- **Dede Korkut alınmadı:** Elde tek boy vardı (Bamsı Beyrek, ~5.900 kelime), Dresden nüshasının noktalamasız transkripsiyonu ve eski yazımla ("kamgan oglı hân bayındır yerinden durmışıdı"). Modelin Türkçesini bozma riski, katkısından büyük.
