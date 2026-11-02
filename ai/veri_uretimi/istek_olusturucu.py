"""Torbadan çekilen malzemeyi öğretmen modele gidecek prompt metnine çevirir.

Prompt şablonları promptlar/*.txt içinde; kodu değiştirmeden düzeltilebilir.
"""
import json
import random

from ai.ortak.ayarlar import PROMPT_KLASORU, TEMA_DOSYASI

EKSTRA_SATIR = {
    "konu": "Kartın derdi şu konuyla ilgili olsun: {}",
    "olay": "Olay: {}",
    "yer": "Yer: {}",
    "zaman": "Zaman: {}",
    "ruh": "Konuşanın ruh hâli: {}",
    "ikilem": "Seçenekler şu ikilemi tartsın: {}",
    "ozellik": "Özellik: {}",
    "uslup": "Anlatım: {}",
}


def _yasak_ornek(adet=10):
    with open(TEMA_DOSYASI, encoding="utf-8") as f:
        return ", ".join(json.load(f)["yasak_kelimeler"][:adet])


def _sablon(tur):
    return (PROMPT_KLASORU / f"{tur}.txt").read_text(encoding="utf-8")


def _ornekler():
    with open(PROMPT_KLASORU / "kart_ornekler.json", encoding="utf-8") as f:
        return json.load(f)


ORNEKLER = _ornekler()


def ornek_metni(o):
    return (f"Metin: {o['metin']}\nSol: {o['sol']}\nSol sonuç: {o['sol_sonuc']}\nSol etki: {o['sol_etki']}\n"
            f"Sağ: {o['sag']}\nSağ sonuç: {o['sag_sonuc']}\nSağ etki: {o['sag_etki']}")


def ornek_sec(malzeme):
    """Her istekte havuzdan farklı bir örnek; konuşanla aynı karakter seçilmez.
    Tek sabit örnek olunca model etkileri olduğu gibi kopyalıyordu (ilk denemede kartların %31'i)."""
    havuz = [o for o in ORNEKLER if o["karakter"] != malzeme.karakter]
    rng = random.Random(json.dumps(malzeme.sozluk(), ensure_ascii=False, sort_keys=True))
    return rng.choice(havuz)


def _ekstra_metni(ekstra, tur="kart"):
    satirlar = []
    for anahtar, deger in ekstra.items():
        if anahtar == "konu" and deger == "serbest":
            satirlar.append("Kartın derdini sen seç; konuşanın işine uygun, sıradan olmayan bir dert olsun.")
        else:
            satir = EKSTRA_SATIR[anahtar].format(deger)
            satirlar.append(satir.replace("Konuşanın", "Karakterin") if tur == "hikaye" else satir)
    return "\n".join(satirlar)


def prompt_olustur(malzeme, torbalar):
    """Malzeme -> öğretmen modele gidecek düz metin."""
    alanlar = {
        "karakter": malzeme.karakter,
        "kelimeler": ", ".join(malzeme.kelimeler),
        "ekstra": _ekstra_metni(malzeme.ekstra, malzeme.tur),
        "yasak": _yasak_ornek(),
    }
    if malzeme.tur == "kart":
        bilgi = torbalar["karakter_bilgi"].get(malzeme.karakter, {})
        alanlar["karakter_ton"] = bilgi.get("ton", "")
        alanlar["karakter_gorev"] = bilgi.get("gorev", "").rstrip(". ")
        alanlar["karakter_soz"] = bilgi.get("sik_sozler", "")
        alanlar["karakter_asla"] = bilgi.get("asla", "")
        alanlar["durum"] = ", ".join(f"{g} {v}" for g, v in malzeme.durum.items())
        alanlar["ornek"] = ornek_metni(ornek_sec(malzeme))
    return _sablon(malzeme.tur).format(**alanlar).replace("\n\n\n", "\n\n")
