# data/

Burada sadece **küçük** veriler durur. Büyükler:

| Ne | Nerede |
| --- | --- |
| Öğretmenin ürettiği bütün hikâye ve kartlar | Google Drive (`02_Veri/uretilen/`) → son hâli Hugging Face (özel veri seti) |
| `train.bin` / `val.bin` | Drive + Hugging Face |
| Tokenizer, model ağırlıkları | Hugging Face (özel depo) |

| Klasör | İçinde |
| --- | --- |
| `torbalar/` | Drive’daki `Torba_Listesi` tablosu (asıl kaynak, bu depoda değil) + kodun okuduğu dışa aktarımlar (.csv / .txt) |
| `uretilen/ham/` | Öğretmen üretiminin ham hâli, iki sürüm: `ham_iliskili/` (saray kartlarında `istedigi` var) ve `ham_iliskisiz/` (`istedigi` yok). jsonl'ler Git LFS'te, bkz. `uretilen/ham/README.md` |
| `uretilen/iliski_deneme/` | İlişki denemesi: Gemma'nın "konuşan hangi kararı istiyor?" sorusuna tutarlılığı (600 kart) |
| `uretilen/ornekler/` | Öğretmen üretiminden küçük örnekler (okumak için) |
| `edebiyat/` | Lisansı temiz metinler (Dede Korkut vb.) + kaynak/lisans notu (2. hafta) |
