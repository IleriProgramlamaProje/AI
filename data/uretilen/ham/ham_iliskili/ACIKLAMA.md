# ham_iliskili — saray kartlarında ilişki (istedigi) bilgisi olan ham veri

Kaynak: `ham/ham_birlesik.jsonl` (147.794 kayıt). Kayıtlar aynen alındı. Tek fark: her saray kartında `istedigi` alanı var.

| Dosya | Kayıt | İçerik |
|---|---|---|
| `hikaye.jsonl` | 101.333 | `tur == "hikaye"` olan kayıtlar (`istedigi` yok) |
| `kart.jsonl` | 46.461 | `tur == "kart"` olan kayıtlar |

## `istedigi` alanı

Kartta konuşan danışmanın, kendi değerlerine göre hükümdardan hangi kararı istediğini gösterir.

Sadece **saray kartlarında** bulunur. Saray kartı şu üç şartı sağlayan karttır:
- `tur == "kart"`
- `malzeme.karakter` şu 10 karakterden biri: Vezir, Başkâtip, Hazinedar, Kale Kumandanı, Akıncı Beyi, Sınır Beyi, Elçi, Saray Hatun, Kervan Başı, Ahi Ustası
- `cikti` "Metin:" ile başlıyor

Saray kartı olmayan kartlarda ve hikâyelerde bu alan yok.

| Değer | Kart | Anlamı |
|---|---|---|
| `"Sol"` | 13.560 | Danışman Sol kararı istiyor |
| `"Sağ"` | 4.421 | Danışman Sağ kararı istiyor |
| `"Belirsiz"` | 1.828 | **İlişki belirsiz:** danışmanın hangi tarafı istediği karttan çıkarılamıyor |

Toplam 19.809 saray kartı.

## Etiketler nereden geldi

- **16.959 kart:** Gemma 4 12B (`data/uretilen/iliski_deneme/Iliski_Etiketleme.ipynb`). Her kart iki kez soruldu. Bir kart ancak iki cevap aynıysa ve Belirsiz değilse etiket aldı.
- **1.022 kart:** Gemma'nın tutarlı cevap veremediği 2.850 kart elle (Claude ile) okundu. Bunlardan 677'si Sol, 345'i Sağ aldı.
- **1.828 kart `"Belirsiz"`:** Kalan kartlarda iki seçenek de karakterin değer/ister/istemez listesine ya eşit uzak ya da eşit ters. Örnek: Başkâtip'in kayıtla ilgisi olmayan bir kıtlık kartı. Bu kartlar `saray/belirsiz_kartlar.md` dosyasında okunabilir hâlde duruyor.

Etiket dosyaları: `saray/etiket/etiket_part*.jsonl` (Gemma), `saray/etiket/etiket_claude.jsonl` (elle). Format `{"h": md5(cikti), "istedigi": ...}`.

## Dikkat

- `"Belirsiz"` olanların 3'ü bozuk kayıt. Metinleri sonsuz "inininin…" tekrarı, seçenekleri boş. İkisi Akıncı Beyi, biri Saray Hatun kartı.
- Etiketlerde Sol ağırlığı var (yaklaşık %76 Sol). Eğitimde dengelemek gerekebilir.
