# uretilen/iliski_deneme/

Öğretmen (Gemma 4 12B) "kartta konuşan hangi kararı istiyor? Sol / Sağ / Belirsiz" sorusunu tutarlı cevaplıyor mu, denemesi.

| Dosya | İçinde |
| --- | --- |
| `Iliski_Denemesi.ipynb` | Colab/Kaggle notebook'u: saray kartlarını alır, her kartı iki kez sorar, tutarlılık ve Belirsiz oranını ölçer, 40 kartı elle kontrole döker |
| `Iliski_Etiketleme.ipynb` | Asıl etiketleme notebook'u: 5 parçaya bölünmüş saray kartlarını Gemma'ya iki kez sorar, etiket dosyalarını yazar, sonunda `ham_birlesik.jsonl` ile birleştirir |
| `iliski_deneme.jsonl` | Denemenin çıktısı, 600 kart (`karakter`, `kart`, `istedigi_1`, `istedigi_2`) |

Bu denemeden sonra bütün saray kartları `Iliski_Etiketleme.ipynb` ile etiketlendi; sonucu `../ham/ham_iliskili/`.
