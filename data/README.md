# data/

Burada sadece **küçük** veriler durur. Büyükler:

| Ne | Nerede |
| --- | --- |
| Öğretmenin ürettiği bütün hikâye ve kartlar | Google Drive (`02_Veri/uretilen/`) → son hâli Hugging Face (özel veri seti) |
| `train.bin` / `val.bin` | Drive + Hugging Face |
| Tokenizer, model ağırlıkları | Hugging Face (özel depo) |

| Klasör | İçinde |
| --- | --- |
| `torbalar/` | `Torba_Listesi.xlsx` (asıl kaynak) + kodun okuduğu dışa aktarımlar (.csv / .txt) |
| `altin_set/` | Ekibin elle ürettiği kartlar (bkz. `altin_set/README.md`) |
| `uretilen/ornekler/` | Öğretmen üretiminden küçük örnekler (okumak için) |
| `edebiyat/` | Lisansı temiz metinler (Dede Korkut vb.) + kaynak/lisans notu (2. hafta) |
