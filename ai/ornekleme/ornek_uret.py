#!/usr/bin/env python3
"""Modelden örnek üretir (görev 3.5): hikâye ya da kart, ve kartlarda biçim geçerliliğini ölçer.

    # 5 hikâye
    python ai/ornekleme/ornek_uret.py --model modeller/1m/en_iyi.pt --tokenizer tokenizer/tokenizer.json --tur hikaye --adet 5
    # 100 kart: rastgele durum + konuşan verilir, model gövdeyi yazar; kaçı biçimce geçerli raporlanır
    python ai/ornekleme/ornek_uret.py --model ... --tokenizer ... --tur kart --adet 100 --sicaklik 0.8 --cikti kartlar.jsonl

Kartta modele durum satırı ve "<kart>" verilir (oyunda da böyle olacak), model "</kart>"a kadar yazar.
Geçerlilik `kart_bicimi.metinden_karta` ile ölçülür (biçim). İçerik kuralları (etki sayısı, düşüş) ayrıca sayılır.
"""
import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

import torch

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from ai.model.model import GPT, Ayar  # noqa: E402
from ai.ortak.kart_bicimi import UNVAN_ANAHTAR, KartBicimHatasi, metinden_karta  # noqa: E402

SON = "<|son|>"
GOSTERGE = ("yonetim", "halk", "para", "ordu")


def model_ac(yol, cihaz):
    k = torch.load(yol, map_location=cihaz)
    model = GPT(Ayar(**k["ayar"]))
    model.load_state_dict(k["model"])
    return model.to(cihaz).eval()


def durum_satiri(rng, konusan=None, konu="serbest"):
    durum = " ".join(f"<{g}:{5 * rng.randint(1, 19)}>" for g in GOSTERGE)
    konusan = konusan or rng.choice(sorted(UNVAN_ANAHTAR.values()))
    return f"{durum} <konu:{konu}> <konuşan:{konusan}>"


def icerik_sorunlari(kart):
    """Biçim geçerli kartta oyunun içerik kuralları: seçenek başına 1-3 etki, en az bir düşüş."""
    sorun = []
    for t in ("sol", "sag"):
        e = kart[t]["etki"]
        if not 1 <= len(e) <= 3:
            sorun.append(f"{t}: {len(e)} etki")
        if e and not any(v < 0 for v in e.values()):
            sorun.append(f"{t}: düşüş yok")
    return sorun


def main(argv=None):
    ap = argparse.ArgumentParser(description="Modelden hikâye/kart üret")
    ap.add_argument("--model", required=True, help="egit.py'nin kaydettiği en_iyi.pt")
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--tur", choices=("hikaye", "kart"), default="kart")
    ap.add_argument("--adet", type=int, default=5)
    ap.add_argument("--sicaklik", type=float, default=0.8)
    ap.add_argument("--top-k", type=int, default=50)
    ap.add_argument("--uzunluk", type=int, default=220, help="en fazla kaç yeni token")
    ap.add_argument("--baslangic", default="", help="hikâye için başlangıç metni (ör. 'Bir gün')")
    ap.add_argument("--konusan", help="kart için sabit konuşan anahtarı (ör. hazinedar)")
    ap.add_argument("--cikti", help="sonuçları jsonl olarak yaz")
    ap.add_argument("--tohum", type=int, default=0)
    ap.add_argument("--cihaz", default="auto")
    a = ap.parse_args(argv)

    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(a.tokenizer))
    son = tok.token_to_id(SON)
    kart_sonu = tok.token_to_id("</kart>")
    cihaz = torch.device(("cuda" if torch.cuda.is_available() else "cpu") if a.cihaz == "auto" else a.cihaz)
    torch.manual_seed(a.tohum)
    rng = random.Random(a.tohum)
    model = model_ac(a.model, cihaz)

    sonuclar, sayac = [], Counter()
    for i in range(a.adet):
        if a.tur == "kart":
            istem = durum_satiri(rng, a.konusan) + "\n<kart>"
            dur = kart_sonu
        else:
            istem = a.baslangic
            dur = son
        ids = [son] + tok.encode(istem).ids if istem else [son]      # <|son|>: yeni belge başlıyor
        x = torch.tensor([ids], dtype=torch.long, device=cihaz)
        y = model.uret(x, a.uzunluk, sicaklik=a.sicaklik, top_k=a.top_k, dur=dur)[0].tolist()
        metin = tok.decode(y[1:], skip_special_tokens=False).replace(SON, "").strip()
        kayit = {"no": i + 1, "metin": metin}
        if a.tur == "kart":
            try:
                kart, _ = metinden_karta(metin)
                sorun = icerik_sorunlari(kart)
                kayit.update(gecerli=True, icerik_sorunlari=sorun)
                sayac["biçim geçerli"] += 1
                sayac["içerik de geçerli"] += not sorun
            except KartBicimHatasi as h:
                kayit.update(gecerli=False, hata=str(h))
                sayac["biçim bozuk"] += 1
        sonuclar.append(kayit)
        print(f"===== {i + 1}" + ("" if a.tur == "hikaye" else f" · {'geçerli' if kayit['gecerli'] else 'bozuk: ' + kayit['hata']}"))
        print(metin, "\n")

    if a.tur == "kart":
        n = len(sonuclar)
        print(f"Biçim geçerli: {sayac['biçim geçerli']}/{n} (%{100 * sayac['biçim geçerli'] / n:.0f}) · "
              f"içerik de geçerli: {sayac['içerik de geçerli']}/{n} · sıcaklık {a.sicaklik}")
    if a.cikti:
        with open(a.cikti, "w", encoding="utf-8") as f:
            for k in sonuclar:
                f.write(json.dumps(k, ensure_ascii=False) + "\n")
    return sonuclar


if __name__ == "__main__":
    main()
