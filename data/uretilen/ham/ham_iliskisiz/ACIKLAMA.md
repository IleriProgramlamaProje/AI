# ham_iliskisiz — ilişki bilgisi olmayan ham veri

Kaynak: `ham/ham_birlesik.jsonl` (147.794 kayıt). Kayıtlar aynen alındı, sadece `istedigi` alanı silindi.

| Dosya | Kayıt | İçerik |
|---|---|---|
| `hikaye.jsonl` | 101.333 | `tur == "hikaye"` olan kayıtlar |
| `kart.jsonl` | 46.461 | `tur == "kart"` olan kayıtlar (saray kartları dahil) |

Hiçbir kayıtta `istedigi` (danışmanın istediği taraf) alanı yok. İlişki/eğilim bilgisi olmadan eğitim için.

Alanlar: `surum, id, tur, malzeme{tur, karakter, kelimeler, ekstra, durum}, prompt, cikti, model, motor, tohum, token, saniye, kaynak`
