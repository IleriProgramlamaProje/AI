#!/usr/bin/env python3
"""O1 · Veri hazırlama: temiz veriyi karışım oranına göre birleştirir, train.bin / val.bin yazar.

    python ai/veri_hazirlama/hazirla.py ~/Downloads/kaydir_veri          # önce: python ai/filtre/filtre.py ~/Downloads/kaydir_veri
    python ai/veri_hazirlama/hazirla.py ~/Downloads/kaydir_veri --oran hikaye=0.65 --oran kart=0.15

Kaynaklar (her biri bir "belge" listesi):
  hikaye   : <veri>/filtre/temiz/*.jsonl, tur == "hikaye" → hikâye metni
  kart     : aynı dosyalar, tur == "kart" → kart_bicimi.egitim_metni (etiketli metin)
  bilgem   : data/edebiyat/bilgem/*.txt      (S3; aralarında boş satır)
  edebiyat : data/edebiyat/ altındaki diğer *.txt (S3)

Adımlar:
  1. Her kaynağın belgeleri karıştırılır (sabit tohum), %5'i val'e ayrılır. Val sadece oranı 0'dan büyük kaynaklardan pay alır, tekrar içermez.
  2. Karışım oranı (README) train için uygulanır. Olmayan kaynağın payı diğerlerine oranla dağıtılır.
     Toplam boyut, oranına göre en kıt kaynağa göre belirlenir; diğer kaynaklardan o kadarı alınır. Hiçbir belge tekrar edilmez.
  3. Train belgeleri kaynaklar birbirine karışacak şekilde sıralanır; kodla() her belgenin sonuna <|son|> koyup uint16 yazar.
  4. Kaynak başına belge ve token sayısı rapor.json'a ve ekrana yazılır.
"""
import argparse
import glob
import json
import random
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from ai.ortak.kart_bicimi import egitim_metni  # noqa: E402
from ai.tokenizer.egit_tokenizer import CIKTI as TOKENIZER  # noqa: E402

# 11 Kasım: altın set çıkarıldı (yasal sebep, Docs/kararlar.md); payı hikâye ve karta dağıtıldı.
ORANLAR = {"hikaye": 0.63, "kart": 0.22, "bilgem": 0.10, "edebiyat": 0.05}
VAL_PAYI = 0.05
TOHUM = 1337


def txt_belgeleri(dosyalar):
    """Boş satırla ayrılmış belgeler."""
    belgeler = []
    for yol in sorted(dosyalar):
        belgeler += [b.strip() for b in Path(yol).read_text(encoding="utf-8").split("\n\n") if b.strip()]
    return belgeler


def kaynaklari_oku(temiz, hazir):
    kaynak = {ad: [] for ad in ORANLAR}
    for yol in sorted(glob.glob(str(Path(temiz) / "*.jsonl"))):
        for satir in open(yol, encoding="utf-8"):
            if not satir.strip():
                continue
            r = json.loads(satir)
            if r["tur"] == "hikaye":
                kaynak["hikaye"].append(r["cikti"])
            elif r["tur"] == "kart":
                kaynak["kart"].append(egitim_metni(r["kart"], r["malzeme"]))
    hazir = Path(hazir)
    kaynak["bilgem"] = txt_belgeleri(glob.glob(str(hazir / "bilgem" / "*.txt")))
    kaynak["edebiyat"] = txt_belgeleri(p for p in glob.glob(str(hazir / "**" / "*.txt"), recursive=True)
                                       if "bilgem" not in Path(p).relative_to(hazir).parts)
    return kaynak


def token_sayilari(tok, belgeler):
    """Her belgenin token sayısı (<|son|> dahil)."""
    return [len(k.ids) + 1 for k in tok.encode_batch(belgeler)] if belgeler else []


def karistir(kaynak, uzunluk, oranlar, val_payi=VAL_PAYI, tohum=TOHUM):
    """(train belgeleri, val belgeleri, rapor) döner. `uzunluk[ad]` belgelerin token sayıları."""
    rnd = random.Random(tohum)
    train_aday, val, rapor = {}, [], {}
    for ad, belgeler in kaynak.items():
        sira = list(range(len(belgeler)))
        if oranlar.get(ad, 0) <= 0:          # kullanılmayan kaynak val'e de girmez
            sira = []
        rnd.shuffle(sira)
        n_val = round(len(sira) * val_payi)
        val += [belgeler[i] for i in sira[:n_val]]
        train_aday[ad] = sira[n_val:]
        rapor[ad] = {"belge": len(belgeler), "token": sum(uzunluk[ad]), "val_belge": n_val,
                     "val_token": sum(uzunluk[ad][i] for i in sira[:n_val])}

    mevcut = {ad: o for ad, o in oranlar.items() if o > 0 and train_aday.get(ad)}
    if not mevcut:
        raise SystemExit("Hiç kaynak yok: önce filtre.py çalıştırılmalı")
    toplam_oran = sum(mevcut.values())
    hedef_oran = {ad: o / toplam_oran for ad, o in mevcut.items()}
    eldeki = {ad: sum(uzunluk[ad][i] for i in train_aday[ad]) for ad in mevcut}
    # Oranı bozmadan alınabilecek en büyük toplam: en kıt kaynak (eldeki / oran) sınırı belirler
    toplam = min(eldeki[ad] / hedef_oran[ad] for ad in mevcut)

    train = []
    for ad in kaynak:
        secilen, sayac = [], 0
        if ad in mevcut:
            butce = hedef_oran[ad] * toplam
            for i in train_aday[ad]:
                if sayac >= butce:
                    break
                secilen.append(i)
                sayac += uzunluk[ad][i]
        train += [kaynak[ad][i] for i in secilen]
        rapor[ad].update({"hedef_oran": round(hedef_oran.get(ad, 0), 4), "train_belge": len(secilen),
                          "train_token": sayac, "kullanilmayan_belge": len(train_aday[ad]) - len(secilen)})
    rnd.shuffle(train)
    train_token = sum(r["train_token"] for r in rapor.values())
    for r in rapor.values():
        r["gercek_oran"] = round(r["train_token"] / train_token, 4) if train_token else 0
    return train, val, rapor


def main():
    ap = argparse.ArgumentParser(description="Temiz veriden karışım oranına göre train.bin / val.bin üretir.")
    ap.add_argument("veri", help="filtre.py'nin çalıştırıldığı veri klasörü")
    ap.add_argument("--temiz", help="temiz jsonl klasörü (varsayılan: <veri>/filtre/temiz)")
    ap.add_argument("--hazir", default=str(KOK / "data" / "edebiyat"), help="hazır veriler (S3); büyük dosyalar Drive'dan")
    ap.add_argument("--tokenizer", default=str(TOKENIZER))
    ap.add_argument("--cikti", help="çıktı klasörü (varsayılan: <veri>/egitim)")
    ap.add_argument("--oran", action="append", default=[], metavar="AD=ORAN", help="örn. --oran hikaye=0.65")
    ap.add_argument("--tohum", type=int, default=TOHUM)
    a = ap.parse_args()

    from tokenizers import Tokenizer
    from ai.tokenizer.kodla import kodla

    veri = Path(a.veri).expanduser().resolve()
    temiz = Path(a.temiz).expanduser() if a.temiz else veri / "filtre" / "temiz"
    cikti = Path(a.cikti).expanduser() if a.cikti else veri / "egitim"
    oranlar = dict(ORANLAR)
    for o in a.oran:
        ad, deger = o.split("=")
        if ad not in oranlar:
            raise SystemExit(f"bilinmeyen kaynak: {ad} ({', '.join(oranlar)})")
        oranlar[ad] = float(deger)

    kaynak = kaynaklari_oku(temiz, a.hazir)
    tok = Tokenizer.from_file(a.tokenizer)
    uzunluk = {ad: token_sayilari(tok, b) for ad, b in kaynak.items()}
    train, val, rapor = karistir(kaynak, uzunluk, oranlar, tohum=a.tohum)

    cikti.mkdir(parents=True, exist_ok=True)
    n_train = kodla(a.tokenizer, train, cikti / "train.bin")
    n_val = kodla(a.tokenizer, val, cikti / "val.bin")
    ozet = {"train_token": n_train, "val_token": n_val, "train_belge": len(train), "val_belge": len(val),
            "tokenizer": a.tokenizer, "tohum": a.tohum, "oranlar": oranlar, "kaynaklar": rapor}
    (cikti / "rapor.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{'kaynak':9} {'belge':>7} {'token':>9} {'train':>9} {'val':>7} {'hedef':>6} {'gerçek':>6} {'kalan':>6}")
    for ad, r in rapor.items():
        print(f"{ad:9} {r['belge']:7} {r['token']:9} {r['train_token']:9} {r['val_token']:7} "
              f"{r['hedef_oran']:6.1%} {r['gercek_oran']:6.1%} {r['kullanilmayan_belge']:6}")
    print(f"\ntrain.bin {n_train:,} token ({len(train)} belge) · val.bin {n_val:,} token ({len(val)} belge) → {cikti}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
