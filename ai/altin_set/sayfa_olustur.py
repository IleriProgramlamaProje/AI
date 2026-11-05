"""Altın set sayfasını güncel torbalarla yeniden üretir.

    python -m ai.altin_set.sayfa_olustur

sablon.html + torbalar (data/torbalar) + tema.json + kart örnekleri -> index.html.
Sayfa iki tür üretir: kart ve hikâye (hikâye malzemesi: isim + fiil + sıfat, olay/yer/zaman/ruh/özellik/üslup).
index.html claude.ai'deki "Altın Set Prompt Üretici" sayfasına yüklenir (ortak liste orada).
Torbalar değişince bu komutu çalıştırıp sayfayı yeniden yayınlayın.
"""
import csv
import json
from pathlib import Path

from ai.ortak.ayarlar import PROMPT_KLASORU, TEMA_DOSYASI, TORBA_KLASORU

KLASOR = Path(__file__).resolve().parent


def _satirlar(dosya):
    return [s.strip() for s in open(TORBA_KLASORU / dosya, encoding="utf-8") if s.strip()]


def _csv(dosya):
    return list(csv.DictReader(open(TORBA_KLASORU / dosya, encoding="utf-8")))


def veri():
    tema = json.load(open(TEMA_DOSYASI, encoding="utf-8"))
    kelimeler = _csv("kelimeler.csv")
    return {
        "karakterler": [{k: c[k] for k in ("anahtar", "unvan", "ton", "gorev", "alan", "sik_sozler", "asla")}
                        for c in tema["karakterler"]],
        "isim": [r["kelime"] for r in kelimeler if r["tur"] == "isim"],
        "sifat": [r["kelime"] for r in kelimeler if r["tur"] == "sıfat"],
        "fiil": [r["kelime"] for r in kelimeler if r["tur"] == "fiil"],
        "konu": _satirlar("konular.txt"),
        "olay": [r["olay"] for r in _csv("olaylar.csv")],
        "yer": _satirlar("yer.txt"),
        "zaman": _satirlar("zaman.txt"),
        "ruh": _satirlar("ruh_hali.txt"),
        "ozellik": _satirlar("ozellikler.txt"),
        "uslup": _satirlar("usluplar.txt"),
        "ikilem": [f'{r["taraf1"]} ↔ {r["taraf2"]}' for r in _csv("ikilem.csv")],
        "yasak": tema["yasak_kelimeler"],
        "kademe": tema["etki_kademeleri"],
        "ornekler": json.load(open(PROMPT_KLASORU / "kart_ornekler.json", encoding="utf-8")),
    }


def main():
    sablon = (KLASOR / "sablon.html").read_text(encoding="utf-8")
    if "/*VERI*/null" not in sablon:
        raise ValueError("sablon.html içinde /*VERI*/null yer tutucusu yok")
    d = json.dumps(veri(), ensure_ascii=False, separators=(",", ":"))
    (KLASOR / "index.html").write_text(sablon.replace("/*VERI*/null", d), encoding="utf-8")
    print(KLASOR / "index.html")


if __name__ == "__main__":
    main()
