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
python -m ai.tokenizer.egit_tokenizer --girdi temiz/model_ciktilari.jsonl temiz/model_kart_egitim.txt
python -m ai.tokenizer.incele
# Hugging Face'e yükleme (HF_TOKEN gerekir):
python -m ai.tokenizer.egit_tokenizer --girdi ... --hf-depo <kurum>/kaydir-tokenizer
```

Kararlar (dosyanın başında ayrıntılı): kelime dağarcığı 8000 · büyük/küçük harf korunur · noktalama ayrı token ·
bütün kart etiketleri (`<kart>`, `<halk++>`, `<para:50>`, `<konuşan:coban>` …, 138 tane) özel token, hiç bölünmez ·
her belgenin sonunda `<|son|>`. Kart kayıtları ham dosyadan alınmaz (satırlı); temiz dosyada `egitim` alanı olunca girer.

3 Kasım ilk deneme: 3.592 hikâye + 1.448 altın set kartı, örnek kart 72 token. `cikti/` Git'e girmez.

7 Kasım son eğitim: 11.539 temiz hikâye + 7.995 temiz kart + 1.542 altın set kartı = 21.076 belge, 2,58 milyon token. Etiketlerin hepsi tek token. Hugging Face'e yükleme, depo ve token belli olunca yapılacak.

**11 Kasım:** Altın set çıkarıldı. 7 Kasım tokenizer'ı altın set metniyle eğitildiği için eğitime başlamadan **bir kez yalnızca temiz Gemma verisiyle yeniden eğitilip dondurulmalı**; ardından `hazirla.py` yeniden çalıştırılır (token numaraları tokenizer'a bağlı).

**26 Kasım (donduruldu):** 73.472 temiz hikâye + 43.462 temiz kart + BİLGEM + edebiyat = 121.389 belge, kelime dağarcığı 8000.
Yeni: tırnak/kesme/tire tek biçim (normalizer), `<istiyor:sol|sag|belirsiz>` etiketleri, 20 boş `<yedek_N>` etiketi.
Temiz kart kaydı (`kart` alanı) doğrudan okunur, ayrı çevirme adımı gerekmez. Eğitildiği komut:

```sh
python -m ai.tokenizer.egit_tokenizer --girdi <filtre>/temiz/hikaye.jsonl <filtre>/temiz/kart.jsonl \
    data/edebiyat/bilgem/bilgem.txt data/edebiyat/omer_seyfettin.txt data/edebiyat/nasreddin_hoca.txt
```

Bu tokenizer'la iki veri üretildi (`--oran edebiyat=0.015`, ~15,4 M train token): `egitim/duz/` ve `egitim/istedigi/` (`hazirla.py --istedigi`).
Yeni etiket gerekirse tokenizer yeniden eğitilmez; `tokenizer.json`'da bir `<yedek_N>`'in adı değiştirilir.
