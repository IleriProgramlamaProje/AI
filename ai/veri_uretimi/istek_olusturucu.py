"""Torbadan çekilen malzemeyi öğretmen modele gidecek prompt metnine çevirir.

Prompt şablonları promptlar/*.txt içinde; kodu değiştirmeden düzeltilebilir.
"""
import json

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


def _ekstra_metni(ekstra):
    satirlar = []
    for anahtar, deger in ekstra.items():
        if anahtar == "konu" and deger == "serbest":
            satirlar.append("Kartın derdini sen seç; konuşanın işine uygun, sıradan olmayan bir dert olsun.")
        else:
            satirlar.append(EKSTRA_SATIR[anahtar].format(deger))
    return "\n".join(satirlar)


def prompt_olustur(malzeme, torbalar):
    """Malzeme -> öğretmen modele gidecek düz metin."""
    alanlar = {
        "karakter": malzeme.karakter,
        "kelimeler": ", ".join(malzeme.kelimeler),
        "ekstra": _ekstra_metni(malzeme.ekstra),
        "yasak": _yasak_ornek(),
    }
    if malzeme.tur == "kart":
        bilgi = torbalar["karakter_bilgi"].get(malzeme.karakter, {})
        alanlar["karakter_ton"] = bilgi.get("ton", "")
        alanlar["karakter_gorev"] = bilgi.get("gorev", "")
        alanlar["karakter_soz"] = bilgi.get("sik_sozler", "")
        alanlar["karakter_asla"] = bilgi.get("asla", "")
        alanlar["durum"] = ", ".join(f"{g} {v}" for g, v in malzeme.durum.items())
    return _sablon(malzeme.tur).format(**alanlar).replace("\n\n\n", "\n\n")
