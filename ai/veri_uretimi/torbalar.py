"""Torbaları okur ve her istek için rastgele malzeme çeker.

Kural (25 Ekim, 1 Kasım kararları):
- Karakter HER ZAMAN var. Kelimeler türüne göre: hikâyede 3 (1 isim + 1 fiil + 1 sıfat, üçü istenir),
  kartta 2 (1 isim + 1 sıfat, en az biri istenir).
- Diğer torbalardan rastgele 1-2 tanesi eklenir.
- Kartlarda ayrıca gösterge durumu (rastgele sayılar) ve ara sıra "serbest konu" var.
"""
import csv
import random
from dataclasses import dataclass, field

from ai.ortak.ayarlar import GOSTERGELER, TORBA_KLASORU

# Hangi torbalar hangi türde "ekstra" olarak seçilebilir
EKSTRA = {
    "hikaye": ["olay", "yer", "zaman", "ruh", "ozellik", "uslup"],
    "kart": ["konu", "olay", "yer", "ruh", "ikilem"],
}
SERBEST_KONU_ORANI = 0.15  # kartların ~%15'inde konu verilmez, model kendi derdini bulur
KELIME_TURU = {"hikaye": ("isim", "fiil", "sıfat"), "kart": ("isim", "sıfat")}


def _satirlar(dosya):
    with open(TORBA_KLASORU / dosya, encoding="utf-8") as f:
        return [s.strip() for s in f if s.strip()]


def _csv(dosya):
    with open(TORBA_KLASORU / dosya, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def torbalari_yukle():
    """Bütün torbaları bir sözlük olarak döndürür."""
    return {
        "karakter": [r["rol"] for r in _csv("karakterler.csv")],
        "karakter_bilgi": {r["rol"]: r for r in _csv("karakterler.csv")},
        "kelime": [r["kelime"] for r in _csv("kelimeler.csv")],
        "kelime_tur": {t: [r["kelime"] for r in _csv("kelimeler.csv") if r["tur"] == t] for t in ("isim", "fiil", "sıfat")},
        "konu": _satirlar("konular.txt"),
        "olay": [r["olay"] for r in _csv("olaylar.csv")],
        "yer": _satirlar("yer.txt"),
        "zaman": _satirlar("zaman.txt"),
        "ruh": _satirlar("ruh_hali.txt"),
        "ikilem": [f'{r["taraf1"]} ↔ {r["taraf2"]}' for r in _csv("ikilem.csv")],
        "ozellik": _satirlar("ozellikler.txt"),
        "uslup": _satirlar("usluplar.txt"),
    }


@dataclass
class Malzeme:
    tur: str                       # "hikaye" ya da "kart"
    karakter: str
    kelimeler: list
    ekstra: dict = field(default_factory=dict)   # ör. {"yer": "han"}
    durum: dict = field(default_factory=dict)    # sadece kart: {"Yönetim": 40, ...}

    def sozluk(self):
        return {"tur": self.tur, "karakter": self.karakter, "kelimeler": self.kelimeler,
                "ekstra": self.ekstra, "durum": self.durum}


def malzeme_cek(torbalar, tur, rng=random):
    """Bir istek için malzeme çeker."""
    if tur not in EKSTRA:
        raise ValueError(f"Bilinmeyen tür: {tur}")
    m = Malzeme(
        tur=tur,
        karakter=rng.choice(torbalar["karakter"]),
        kelimeler=[rng.choice(torbalar["kelime_tur"][t]) for t in KELIME_TURU[tur]],
    )
    adaylar = list(EKSTRA[tur])
    ekstra_adet = rng.randint(1, 2)
    if tur == "kart":
        adaylar.remove("konu")
        if rng.random() < SERBEST_KONU_ORANI:
            m.ekstra["konu"] = "serbest"
        else:
            m.ekstra["konu"] = rng.choice(torbalar["konu"])
            ekstra_adet -= 1
    for anahtar in rng.sample(adaylar, ekstra_adet):
        m.ekstra[anahtar] = rng.choice(torbalar[anahtar])
    if tur == "kart":
        m.durum = {g: 5 * rng.randint(1, 19) for g in GOSTERGELER}
    return m
