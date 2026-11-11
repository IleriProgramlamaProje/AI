#!/usr/bin/env python3
"""Ön eğitim (görev 3.3). train.bin üzerinde modeli eğitir, val.bin ile ölçer.

    python ai/egitim/egit.py --boyut ai/model/boyutlar/1m.yaml --veri ~/Downloads/kaydir_veri/egitim \\
        --tokenizer ~/Downloads/kaydir_veri/tokenizer/tokenizer.json --cikti ~/Downloads/kaydir_veri/modeller/1m

Döngü (her adım):
  1. train.bin'den rastgele `yigin` tane `baglam` uzunluğunda parça al; hedef aynı parçanın bir token kaydırılmışı.
  2. Model her konumda bir sonraki token'ı tahmin eder, kayıp (cross-entropy) hesaplanır.
  3. Geri yayılım: her parametrenin kaybı nasıl etkilediği bulunur; AdamW parametreleri biraz düzeltir.
  4. Her `--olcum-araligi` adımda train ve val kaybı ölçülür, kayip.csv'ye yazılır.
     Val kaybı en iyiyse model `en_iyi.pt` olarak kaydedilir. `--sabir` ölçüm boyunca iyileşmezse
     eğitim durur (erken durdurma: model ezberlemeye başlamış demektir).

Adım sayısı verilmezse `tur` (yaml) kadar: veri `tur` kez okunacak kadar adım. 4 tur genel kural.
Öğrenme oranı: ilk %5 adımda ısınma (0'dan yukarı), sonra kosinüsle %10'una kadar iner.
GPU varsa fp16 karışık hassasiyet (T4 bf16 desteklemez); kesilirse `--devam` ile son.pt'den sürer.
"""
import argparse
import csv
import json
import math
import sys
import time
from contextlib import nullcontext
from pathlib import Path

import numpy as np
import torch
import yaml

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from ai.model.model import GPT, Ayar  # noqa: E402


def parca_al(veri, yigin, baglam, cihaz):
    """Rastgele `yigin` tane pencere: x = token[i:i+baglam], y = token[i+1:i+1+baglam]."""
    i = torch.randint(len(veri) - baglam - 1, (yigin,))
    x = torch.stack([torch.from_numpy(veri[j:j + baglam].astype(np.int64)) for j in i.tolist()])
    y = torch.stack([torch.from_numpy(veri[j + 1:j + 1 + baglam].astype(np.int64)) for j in i.tolist()])
    if cihaz.type == "cuda":
        return x.pin_memory().to(cihaz, non_blocking=True), y.pin_memory().to(cihaz, non_blocking=True)
    return x.to(cihaz), y.to(cihaz)


@torch.no_grad()
def kayip_olc(model, veriler, yigin, baglam, cihaz, ctx, tekrar):
    """Her veri için `tekrar` rastgele yığının ortalama kaybı."""
    model.eval()
    sonuc = {}
    for ad, veri in veriler.items():
        kayiplar = []
        for _ in range(tekrar):
            x, y = parca_al(veri, yigin, baglam, cihaz)
            with ctx:
                _, kayip = model(x, y)
            kayiplar.append(kayip.item())
        sonuc[ad] = float(np.mean(kayiplar))
    model.train()
    return sonuc


def ogrenme_orani(adim, toplam, tepe, isinma):
    if adim < isinma:
        return tepe * (adim + 1) / isinma
    oran = (adim - isinma) / max(1, toplam - isinma)
    return tepe * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(1.0, oran))))


def iyilestirici(model, oran, agirlik_cezasi):
    """AdamW. Ağırlık cezası sadece 2 boyutlu parametrelere (matrisler, gömme); LayerNorm'a uygulanmaz."""
    p = [x for x in model.parameters() if x.requires_grad]
    gruplar = [{"params": [x for x in p if x.dim() >= 2], "weight_decay": agirlik_cezasi},
               {"params": [x for x in p if x.dim() < 2], "weight_decay": 0.0}]
    return torch.optim.AdamW(gruplar, lr=oran, betas=(0.9, 0.95))


def kaydet(yol, model, opt, adim, en_iyi, boyut):
    torch.save({"model": model.state_dict(), "ayar": vars(model.ayar), "opt": opt.state_dict(),
                "adim": adim, "en_iyi_val": en_iyi, "boyut": boyut}, yol)


def grafik(csv_yol, png_yol):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    satirlar = list(csv.DictReader(open(csv_yol, encoding="utf-8")))
    if not satirlar:
        return
    adim = [int(s["adim"]) for s in satirlar]
    plt.figure(figsize=(7, 4))
    plt.plot(adim, [float(s["train"]) for s in satirlar], label="train")
    plt.plot(adim, [float(s["val"]) for s in satirlar], label="val")
    plt.xlabel("adım")
    plt.ylabel("kayıp")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(png_yol, dpi=120)
    plt.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Küçük GPT ön eğitimi")
    ap.add_argument("--boyut", required=True, help="ai/model/boyutlar/1m.yaml gibi")
    ap.add_argument("--veri", required=True, help="train.bin ve val.bin'in olduğu klasör")
    ap.add_argument("--tokenizer", help="tokenizer.json (sözlük boyutu buradan okunur; yoksa yaml'daki)")
    ap.add_argument("--cikti", required=True, help="kayıt noktaları ve kayip.csv buraya")
    ap.add_argument("--adim", type=int, help="toplam adım (verilmezse yaml'daki `tur`dan hesaplanır)")
    ap.add_argument("--yigin", type=int)
    ap.add_argument("--biriktir", type=int, default=1, help="gradyan birikimi: bellek yetmezse yığını böl")
    ap.add_argument("--ogrenme-orani", type=float)
    ap.add_argument("--agirlik-cezasi", type=float, default=0.1)
    ap.add_argument("--olcum-araligi", type=int, default=250)
    ap.add_argument("--olcum-tekrar", type=int, default=40)
    ap.add_argument("--sabir", type=int, default=6, help="val bu kadar ölçüm iyileşmezse dur (0: kapalı)")
    ap.add_argument("--sure-saat", type=float, default=0, help="en fazla bu kadar saat (0: sınırsız); son.pt'ye kaydedip durur")
    ap.add_argument("--devam", action="store_true", help="cikti/son.pt'den sür")
    ap.add_argument("--cihaz", default="auto")
    ap.add_argument("--tohum", type=int, default=1337)
    a = ap.parse_args(argv)

    boyut = yaml.safe_load(open(a.boyut, encoding="utf-8"))
    if a.tokenizer:
        from tokenizers import Tokenizer
        boyut["sozluk"] = Tokenizer.from_file(str(a.tokenizer)).get_vocab_size()
    ayar = Ayar.sozlukten(boyut)
    yigin = a.yigin or boyut.get("yigin", 32)
    tepe = a.ogrenme_orani or boyut.get("ogrenme_orani", 1e-3)

    cihaz = torch.device(("cuda" if torch.cuda.is_available() else "cpu") if a.cihaz == "auto" else a.cihaz)
    torch.manual_seed(a.tohum)
    ctx = torch.autocast("cuda", dtype=torch.float16) if cihaz.type == "cuda" else nullcontext()
    olcekleyici = torch.amp.GradScaler("cuda", enabled=cihaz.type == "cuda")

    veri_klasoru = Path(a.veri).expanduser()
    train = np.memmap(veri_klasoru / "train.bin", dtype=np.uint16, mode="r")
    val = np.memmap(veri_klasoru / "val.bin", dtype=np.uint16, mode="r")
    if len(val) <= ayar.baglam + 1 or len(train) <= ayar.baglam + 1:
        raise SystemExit("train.bin / val.bin bağlamdan kısa: önce hazirla.py çalıştırılmalı")
    en_buyuk = int(max(train.max(), val.max()))
    if en_buyuk >= ayar.sozluk:
        raise SystemExit(f"veride {en_buyuk} numaralı token var ama sözlük {ayar.sozluk}: train.bin başka tokenizer'la üretilmiş")

    adim_basi = yigin * a.biriktir * ayar.baglam
    toplam = a.adim or max(1, int(boyut.get("tur", 4) * len(train) / adim_basi))
    isinma = max(1, int(0.05 * toplam))

    cikti = Path(a.cikti).expanduser()
    cikti.mkdir(parents=True, exist_ok=True)
    model = GPT(ayar).to(cihaz)
    opt = iyilestirici(model, tepe, a.agirlik_cezasi)
    baslangic, en_iyi, sabir = 0, float("inf"), 0
    csv_yol = cikti / "kayip.csv"
    if a.devam and (cikti / "son.pt").exists():
        k = torch.load(cikti / "son.pt", map_location=cihaz)
        model.load_state_dict(k["model"])
        opt.load_state_dict(k["opt"])
        baslangic, en_iyi = k["adim"], k["en_iyi_val"]
        print(f"son.pt'den devam: adım {baslangic}, en iyi val {en_iyi:.4f}")
    elif csv_yol.exists():
        csv_yol.unlink()
    if not csv_yol.exists():
        csv_yol.write_text("adim,train,val,ogrenme_orani,saniye\n", encoding="utf-8")

    n = model.parametre_sayisi()
    print(f"Model {n / 1e6:.2f}M parametre · cihaz {cihaz} · train {len(train):,} token · val {len(val):,} token")
    print(f"Adım {toplam:,} (adım başı {adim_basi:,} token, ~{toplam * adim_basi / len(train):.1f} tur) · ısınma {isinma}")
    (cikti / "ayar.json").write_text(json.dumps({"model": vars(ayar), "parametre": n, "yigin": yigin,
                                                 "biriktir": a.biriktir, "ogrenme_orani": tepe, "adim": toplam,
                                                 "train_token": len(train), "val_token": len(val), "boyut": a.boyut},
                                                ensure_ascii=False, indent=1), encoding="utf-8")

    t0 = time.time()
    model.train()
    x, y = parca_al(train, yigin, ayar.baglam, cihaz)
    adim = baslangic
    for adim in range(baslangic, toplam):
        oran = ogrenme_orani(adim, toplam, tepe, isinma)
        for g in opt.param_groups:
            g["lr"] = oran

        if adim % a.olcum_araligi == 0 or adim == toplam - 1:
            k = kayip_olc(model, {"train": train, "val": val}, yigin, ayar.baglam, cihaz, ctx, a.olcum_tekrar)
            gecen = time.time() - t0
            with open(csv_yol, "a", encoding="utf-8") as f:
                f.write(f"{adim},{k['train']:.4f},{k['val']:.4f},{oran:.6f},{gecen:.0f}\n")
            isaret = ""
            if k["val"] < en_iyi:
                en_iyi, sabir, isaret = k["val"], 0, " *en iyi"
                kaydet(cikti / "en_iyi.pt", model, opt, adim, en_iyi, a.boyut)
            elif adim > baslangic:
                sabir += 1
            print(f"adım {adim:6d}/{toplam} · train {k['train']:.3f} · val {k['val']:.3f} · oran {oran:.2e} · {gecen / 60:.1f} dk{isaret}", flush=True)
            kaydet(cikti / "son.pt", model, opt, adim, en_iyi, a.boyut)
            if a.sabir and sabir >= a.sabir:
                print(f"Val {a.sabir} ölçümdür iyileşmiyor: erken durduruldu (ezber başlıyor).")
                break
            if a.sure_saat and gecen > a.sure_saat * 3600:
                print("Süre doldu: son.pt kaydedildi, --devam ile sürdürülebilir.")
                break

        for mikro in range(a.biriktir):
            with ctx:
                _, kayip = model(x, y)
                kayip = kayip / a.biriktir
            x, y = parca_al(train, yigin, ayar.baglam, cihaz)   # sonraki yığın, GPU çalışırken hazırlanır
            olcekleyici.scale(kayip).backward()
        olcekleyici.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)  # aşırı büyük adımları kırp
        olcekleyici.step(opt)
        olcekleyici.update()
        opt.zero_grad(set_to_none=True)

    grafik(csv_yol, cikti / "kayip.png")
    print(f"Bitti: en iyi val {en_iyi:.4f} → {cikti / 'en_iyi.pt'} · grafik {cikti / 'kayip.png'}")
    return en_iyi


if __name__ == "__main__":
    main()
