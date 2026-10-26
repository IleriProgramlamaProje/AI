# Veri üretimi

Mevcut kod: `torbalar.py` → `istek_olusturucu.py` → `uretici.py`. Öğretmen model ayarı `ai/ortak/ayarlar.py` içindedir. Önce Colab'da `hiz_olcumu.ipynb`, sonra `uretim.ipynb` çalıştırılır. Gerçek GPU denemesi ve paket sürümlerinin sabitlenmesi henüz tamamlanmadı.

Her istekte karakter + üç kelime vardır. Ek torbalardan 1–2 tanesi seçilir. Kartta konu yaklaşık %85 belirli, %15 serbesttir: belirli konu 1–2 ek torbanın birini oluşturur; serbest konu işaretine ek olarak 1–2 torba seçilir. Rol/konu uyumunu garanti eden bir tablo henüz yoktur; prompt bunu öğretmenden ister.

`promptlar/hikaye.txt` hikâye, `promptlar/kart.txt` etiketli kart gövdesi ister. Üretici ham çıktıyı kaydeder; biçim/içerik doğrulaması ve JSON karta dönüştürme henüz uygulanmadı. Eski `Metin: / Sol:` biçimli çıktılarla yeni etiketli çıktıları aynı dosyaya eklemeyin.

## Çalıştırma ve devam

AI depo kökünden, öğretmen bağımlılıklarının kurulu olduğu GPU ortamında:

```sh
python -m ai.veri_uretimi.uretici --tur kart --adet 100 --grup 8 --tohum 42 --cikti /tmp/kartlar.jsonl
```

`adet` eklenecek kayıt sayısı değil, dosyanın ulaşacağı toplamdır. `grup` pozitif olmalı. `auto` önce vLLM, açılmazsa Transformers dener; grup boyutunu GPU belleğine göre ölçerek artırın. CPU ortamında bu komutun performansı doğrulanmadı.

Her satırda `surum`, `id`, `tur`, `malzeme`, `prompt`, `cikti`, `model`, `tohum`, `token`, `saniye` bulunur. Kayıt sürümü 2'dir. Devam etmeden tür/model/tohum/sürüm, sıra numarası, boş çıktı ve JSONL satır sonları kontrol edilir. Uyuşmazlıkta dosyaya yazılmaz. Eski sürüm dosyalarını koruyup yeni çıktı adı seçin; bozuk dosyayı yedekleyip incelemeden satır silmeyin.

Aynı kod, torbalar ve tohumla devam, önceki malzemeleri atlayarak sürer; dil modelinin çıktısının birebir aynı olması garanti edilmez. Torbalar veya prompt değişirse yeni dosya kullanın. Aynı dosyaya eşzamanlı iki üretici yazmamalı; notebook'ta hesap/gece adları ayrı tutulur.

Her grup diske aktarılır. Kesintide yarım JSON satırı kalırsa sonraki çalışma açık hata verir. Eksik/boş motor cevabı grubu yazmadan reddedilir. Çıktı kalitesi için filtre yine gereklidir.

## Colab

Notebook AI ve Docs depolarını ayrı klonlar, mevcut kopyaları silmez. GitHub token'ı gizli girişten alınır ve yalnız Git alt sürecine geçici yetki olarak verilir. Token'ı hücreye veya URL'ye koymayın. Hugging Face model erişimi ayrıca gerekir.

Hız ölçümü yeni zaman damgalı dosya kullanır; böylece önceki ölçümün kayıtlarını okuyup üretimi atlamaz. Ölçülen süre model yüklemesini içermez. Gece hedefleri ham kayıt sayısıdır; nihai eğitim karışımı token sayısı üzerinden hazırlanacaktır.
