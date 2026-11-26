# uretilen/egitim/ · eğitim verisi (26 Kasım, tokenizer donduruldu)

| Klasör | Ne | train.bin | val.bin |
|---|---|---:|---:|
| `duz/` | Hikâyede kelime kuralı açık | 15,36 M token | 0,89 M |
| `istedigi/` | `duz` + saray kartlarında `<istiyor:sol\|sag\|belirsiz>` | 15,36 M token | 0,90 M |
| `kelimesiz/` | Hikâyede kelime kuralı kapalı (`filtre.py --kelimeye-bakma`) | 17,20 M token | 1,04 M |

Her klasörde `train.bin`, `val.bin` (uint16 token numaraları, belge sonunda `<|son|>`), `tokenizer.json` (kökteki ile aynı) ve `rapor.json` (kaynak başına belge/token).
Hepsi `--oran edebiyat=0.015` ile. Nasıl eğitilir ve nasıl yeniden üretilir: `Docs/egitim_rehberi.md`.
Bu dosyalar düz Git'te (LFS değil): eğitim için ham veriyi indirmek gerekmez, `GIT_LFS_SKIP_SMUDGE=1 git pull` yeter.
