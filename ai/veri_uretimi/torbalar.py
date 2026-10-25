"""Torbaları okur ve her istek için rastgele malzeme çeker.

Kural (25 Ekim kararı):
- Karakter ve 3 kelime HER ZAMAN var.
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
        kelimeler=rng.sample(torbalar["kelime"], 3),
    )
    adaylar = list(EKSTRA[tur])
    if tur == "kart" and rng.random() < SERBEST_KONU_ORANI:
        adaylar.remove("konu")
        m.ekstra["konu"] = "serbest"
    for anahtar in rng.sample(adaylar, rng.randint(1, 2)):
        m.ekstra[anahtar] = rng.choice(torbalar[anahtar])
    if tur == "kart":
        m.durum = {g: 5 * rng.randint(1, 19) for g in GOSTERGELER}
    return m
