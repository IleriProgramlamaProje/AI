# uretilen/ham/

Öğretmen üretiminin ham hâli (`ham_birlesik.jsonl`, 147.794 kayıt), iki sürüm.

| Klasör | İçinde |
| --- | --- |
| `ham_iliskili/` | `hikaye.jsonl` (101.333), `kart.jsonl` (46.461). Saray kartlarında `istedigi` alanı var: `"Sol"` / `"Sağ"` / `"Belirsiz"` |
| `ham_iliskisiz/` | Aynı kayıtlar, `istedigi` alanı silinmiş. Ek olarak `belirsiz_kartlar.md` (Belirsiz etiketli 1.825 saray kartı, okunabilir hâlde) |

Alanlar ve etiketlerin nereden geldiği her klasördeki `ACIKLAMA.md`'de.

## Git LFS

`.jsonl` dosyaları 100 MB'ı geçtiği için **Git LFS** ile tutuluyor (`.gitattributes`).
Clone'dan önce bir kez:

```bash
git lfs install
```

LFS olmadan clone'larsan jsonl'ler küçük işaretçi dosyası olarak gelir; sonradan `git lfs pull` ile indirilir.
