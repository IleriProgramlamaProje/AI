# tokenizer/ (M5)

| Dosya | Ne |
| --- | --- |
| `egit_tokenizer.py` | BPE tokenizer eğitir (`tokenizers`), `cikti/tokenizer.json`'a yazar, istenirse Hugging Face'e yükler |
| `incele.py` | 20 örnek cümlenin bölünüşü, kart etiketlerinin tek token olduğu, bölünüp birleştirilen kartın okunduğu |
| `incele.ipynb` | Aynısı defterde, kendi cümleni denemek için |
| `kodla.py` | Belgeleri `train.bin`/`val.bin` biçimine çevirir (uint16, belge sonunda `<|son|>`); `hazirla.py` bunu çağırır |

```sh
cd AI
# temiz kartları önce eğitim metnine çevir (temiz hikâyeler jsonl'den doğrudan okunur)
python -m ai.ortak.kart_bicimi temiz/model_ciktilari.jsonl temiz/model_kart_egitim.txt
python -m ai.tokenizer.egit_tokenizer --girdi temiz/model_ciktilari.jsonl temiz/model_kart_egitim.txt data/altin_set/ham/altin_set_egitim.txt data/altin_set/ham/altin_ek_egitim.txt
python -m ai.tokenizer.incele
# Hugging Face'e yükleme (HF_TOKEN gerekir):
python -m ai.tokenizer.egit_tokenizer --girdi ... --hf-depo <kurum>/kaydir-tokenizer
```

Kararlar (dosyanın başında ayrıntılı): kelime dağarcığı 8000 · büyük/küçük harf korunur · noktalama ayrı token ·
bütün kart etiketleri (`<kart>`, `<halk++>`, `<para:50>`, `<konuşan:coban>` …, 138 tane) özel token, hiç bölünmez ·
her belgenin sonunda `<|son|>`. Kart kayıtları ham dosyadan alınmaz (satırlı); temiz dosyada `egitim` alanı olunca girer.

3 Kasım ilk deneme: 3.592 hikâye + 1.448 altın set kartı, örnek kart 72 token. `cikti/` Git'e girmez.

7 Kasım son eğitim: 11.539 temiz hikâye + 7.995 temiz kart + 1.542 altın set kartı = 21.076 belge, 2,58 milyon token. Etiketlerin hepsi tek token. Hugging Face'e yükleme, depo ve token belli olunca yapılacak.
