# bilgem/

`bilgem.txt`: [BILGEM-AI/BILGE-Synthetic-Stories](https://huggingface.co/datasets/BILGEM-AI/BILGE-Synthetic-Stories) veri setinden temizlenmiş parça. Lisans: **Apache 2.0**.
27B parametreli bir modelle Cosmopedia yöntemiyle üretilmiş sentetik Türkçe hikâyeler.

Üreten: `python ai/veri_hazirlama/bilgem_indir.py --dosya 6 --mb 150 --hedef 1500000`
(kaynak dosya: `train-00006-of-00043_generated.json`, ilk 150 MB).

| | Sayı |
| --- | --- |
| Okunan kayıt | 40,217 |
| Uygun (temizlikten geçen) | 7,176 (masal tarzı 6,052) |
| Dosyaya yazılan | 4,217 (masal tarzı 4,217) |
| Kelime | 1,500,286 |

Elenenler:

| Sebep | Kayıt |
| --- | --- |
| ingilizce | 6,619 |
| forum | 11,443 |
| modern | 14,969 |
| kisa | 10 |
| tekrar | 0 |

Kurallar betiğin başındaki açıklamada. Belgeler arasında boş satır var.
