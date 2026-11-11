"""Kart biçimleri arasında çeviri (görev S2). Bkz. Docs/kart_formati.md 2. ve 3. bölüm.

Bir kart üç biçimde dolaşır:
  1. Temiz kayıt (S1 filtresinin çıktısı): iki Python sözlüğü, `kart` ve `malzeme`.
  2. Etiketli metin: modelin okuyup yazdığı biçim (eğitim verisi).
  3. Oyun JSON'u: Godot'nun okuduğu biçim.

    egitim_metni(kart, malzeme)  1 -> 2
    oyun_json(kart, malzeme)     1 -> 3
    metinden_karta(metin)        2 -> 1   (bozuk metinde KartBicimHatasi fırlatır)
    satirli_karta(cikti)         öğretmenin satırlı çıktısı -> kart (Metin:/Sol:/.../Sağ etki:)

Temiz kart dosyasını eğitim metnine çevirmek için:
    python -m ai.ortak.kart_bicimi temiz/model_ciktilari.jsonl temiz/model_kart_egitim.txt

Temiz kayıt şöyle görünür:
    kart = {"metin": "...",
            "sol": {"karar": "Ambarı aç", "sonuc": "...", "etki": {"halk": 10, "para": -5}},
            "sag": {"karar": "...", "sonuc": "...", "etki": {...}}}
    malzeme = {"karakter": "Hazinedar",                       # unvan, tema.json'daki gibi
               "durum": {"Yönetim": 50, "Halk": 40, "Para": 25, "Ordu": 60},
               "ekstra": {"konu": "ekmek"}}                   # konu yoksa "serbest" sayılır
"""
import argparse
import json
import re

from ai.ortak.ayarlar import ETKI_KADEMELERI, GOSTERGELER, TEMA_DOSYASI


class KartBicimHatasi(ValueError):
    """Etiketli metin beklenen biçimde değil (eksik etiket, bilinmeyen gösterge, geçersiz işaret...)."""


# ---------- tablolar (hepsi projedeki tek kaynaktan okunur, elle yazılmaz) ----------

with open(TEMA_DOSYASI, encoding="utf-8") as _f:
    _KARAKTERLER = json.load(_f)["karakterler"]

UNVAN_ANAHTAR = {k["unvan"]: k["anahtar"] for k in _KARAKTERLER}   # "Akıncı Beyi" -> "akinci_beyi"
ANAHTAR_UNVAN = {v: k for k, v in UNVAN_ANAHTAR.items()}           # "akinci_beyi" -> "Akıncı Beyi"
ETIKET_AD = {v: k for k, v in GOSTERGELER.items()}                 # "yonetim" -> "Yönetim"
SIRA = list(GOSTERGELER.values())                                  # yonetim, halk, para, ordu: etiketler hep bu sırada
ISARET = {v: k for k, v in ETKI_KADEMELERI.items()}                # 10 -> "++", -15 -> "---"

KAYNAKLAR = ("ogretmen", "model", "altin_set")
SERBEST = "serbest"
_ASCII = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "à": "a", "î": "i", "û": "u"})


# ---------- küçük yardımcılar ----------

def _kucuk(s):
    """Türkçe küçük harf: Python'un lower()'ı 'İ'yi 'i̇' (noktalı iki karakter) yapar, onu önler."""
    return s.replace("İ", "i").replace("I", "ı").lower()


def konu_ascii(konu):
    """JSON'daki konu: küçük harf ASCII, alt çizgili. "Kale onarımı" -> "kale_onarimi"."""
    s = _kucuk(konu).translate(_ASCII)
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _konu(malzeme):
    return (malzeme.get("ekstra") or {}).get("konu") or SERBEST


def _anahtar(unvan):
    if unvan not in UNVAN_ANAHTAR:
        raise KeyError(f"tema.json'da böyle bir karakter yok: {unvan!r}")
    return UNVAN_ANAHTAR[unvan]


def _etki_etiketleri(etki):
    """{"para": 10, "halk": -10} -> "<halk--> <para++>"  (sıra hep yonetim, halk, para, ordu)."""
    for g, v in etki.items():
        if g not in SIRA:
            raise KeyError(f"bilinmeyen gösterge: {g!r}")
        if v not in ISARET:
            raise ValueError(f"geçersiz etki değeri: {g}={v} (5, 10, 15 ya da eksileri olmalı)")
    return " ".join(f"<{g}{ISARET[etki[g]]}>" for g in SIRA if g in etki)


# ---------- 1 -> 2: eğitim metni ----------

def egitim_metni(kart, malzeme):
    """Temiz kayıttan etiketli metin. Örnek çıktı:

    <yonetim:10> <halk:15> <para:50> <ordu:25> <konu:serbest> <konuşan:coban>
    <kart> Koyunları otlatırken ...
    <sol> Tüccarları içeri al <yonetim-> <halk--> <para++>
    <sonuc> Yabancılar pazara mal getirdi ...
    <sag> Tüccarları kapıdan koval <halk+> <para-->
    <sonuc> Sürüler ve otlaklar korundu ...
    </kart>
    """
    # Durum satırı: dört gösterge (görünen ad -> etiket adı), sonra konu (boşluk -> _), sonra konuşan anahtarı.
    durum = " ".join(f"<{etiket}:{int(malzeme['durum'][ad])}>" for ad, etiket in GOSTERGELER.items())
    konu = re.sub(r"\s+", "_", _konu(malzeme).strip())
    satirlar = [f"{durum} <konu:{konu}> <konuşan:{_anahtar(malzeme['karakter'])}>",
                f"<kart> {kart['metin'].strip()}"]
    for taraf in ("sol", "sag"):
        s = kart[taraf]
        satirlar.append(f"<{taraf}> {s['karar'].strip()} {_etki_etiketleri(s['etki'])}")
        satirlar.append(f"<sonuc> {s['sonuc'].strip()}")
    satirlar.append("</kart>")
    return "\n".join(satirlar)


# ---------- 1 -> 3: oyun JSON'u ----------

def oyun_json(kart, malzeme, kaynak="ogretmen"):
    """kart_formati.md 3. bölümdeki sözlük. Farklar: karar -> etiket, konu ASCII, konuşan anahtar."""
    if kaynak not in KAYNAKLAR:
        raise ValueError(f"kaynak {KAYNAKLAR} içinden olmalı, geldi: {kaynak!r}")
    def secenek(s):
        _etki_etiketleri(s["etki"])  # sadece kontrol: bilinmeyen gösterge / geçersiz değer varsa hata
        return {"etiket": s["karar"].strip(), "etki": {g: s["etki"][g] for g in SIRA if g in s["etki"]}, "sonuc": s["sonuc"].strip()}
    return {
        "konusan": _anahtar(malzeme["karakter"]),
        "konu": konu_ascii(_konu(malzeme)),
        "metin": kart["metin"].strip(),
        "sol": secenek(kart["sol"]),
        "sag": secenek(kart["sag"]),
        "kaynak": kaynak,
        "lisans": "sadece_ders",
    }


# ---------- 2 -> 1: etiketli metinden karta ----------

_DURUM_ETIKET = re.compile(r"<([^:<>\s]+):([^<>]*)>")
_GOVDE = re.compile(r"<kart>(.*?)<sol>(.*?)<sonuc>(.*?)<sag>(.*?)<sonuc>(.*?)</kart>", re.S)
_ETKI = re.compile(r"<([a-z]+)([^<>]*)>")


def _durum_oku(satir):
    """İlk satır -> (durum, konu, karakter)."""
    etiketler = dict(_DURUM_ETIKET.findall(satir))
    durum = {}
    for etiket in SIRA:
        if etiket not in etiketler:
            raise KartBicimHatasi(f"durum satırında <{etiket}:…> yok")
        deger = etiketler[etiket].strip()
        if not deger.isdigit() or not 0 <= int(deger) <= 100:
            raise KartBicimHatasi(f"<{etiket}:{deger}>: 0-100 arası bir sayı olmalı")
        durum[ETIKET_AD[etiket]] = int(deger)
    konu = etiketler.get("konu", "").strip()
    if not konu:
        raise KartBicimHatasi("durum satırında <konu:…> yok")
    anahtar = etiketler.get("konuşan", etiketler.get("konusan", "")).strip()
    if anahtar not in ANAHTAR_UNVAN:
        raise KartBicimHatasi(f"bilinmeyen konuşan: {anahtar!r} (tema.json'da yok)")
    return durum, konu.replace("_", " "), ANAHTAR_UNVAN[anahtar]


def _secenek_oku(ad, govde, sonuc):
    """"Ambarı aç <halk++> <para->" -> {"karar": "Ambarı aç", "etki": {...}, "sonuc": ...}."""
    govde = govde.strip()
    ilk = govde.find("<")
    if ilk == -1:
        raise KartBicimHatasi(f"<{ad}>: etki etiketi yok (en az 1 gösterge etkilenmeli)")
    karar, etiketler = govde[:ilk].strip(), govde[ilk:]
    if not karar:
        raise KartBicimHatasi(f"<{ad}>: karar boş")
    if _ETKI.sub("", etiketler).strip():
        raise KartBicimHatasi(f"<{ad}>: etiketlerin arasında ya da sonunda fazladan yazı var: {etiketler!r}")
    etki = {}
    for g, isaret in _ETKI.findall(etiketler):
        if g not in SIRA:
            raise KartBicimHatasi(f"<{ad}>: bilinmeyen gösterge <{g}{isaret}>")
        if isaret not in ETKI_KADEMELERI:
            raise KartBicimHatasi(f"<{ad}>: geçersiz işaret <{g}{isaret}> (+ ++ +++ - -- --- olmalı)")
        if g in etki:
            raise KartBicimHatasi(f"<{ad}>: {g} iki kez yazılmış")
        etki[g] = ETKI_KADEMELERI[isaret]
    if not 1 <= len(etki) <= 3:
        raise KartBicimHatasi(f"<{ad}>: {len(etki)} gösterge etkileniyor (1-3 olmalı)")
    sonuc = sonuc.strip()
    if not sonuc:
        raise KartBicimHatasi(f"<{ad}>: sonuç cümlesi boş")
    return {"karar": karar, "sonuc": sonuc, "etki": etki}


def metinden_karta(metin):
    """Etiketli metin -> (kart, malzeme). Biçim bozuksa KartBicimHatasi.

    </kart>'tan sonra gelen her şey atılır (model bazen devam edip yeni kart başlatır).
    İçerik kuralları ("iki seçenek de en az bir göstergeyi düşürsün" gibi) burada değil,
    S1 filtresinde ve oyunun doğrulayıcısında kontrol edilir; bu fonksiyon biçime bakar.
    """
    metin = metin.strip()
    if "\n" not in metin:
        raise KartBicimHatasi("durum satırı ya da kart gövdesi yok")
    ilk_satir, govde = metin.split("\n", 1)
    durum, konu, karakter = _durum_oku(ilk_satir)
    if "</kart>" not in govde:
        raise KartBicimHatasi("</kart> yok (metin yarıda kesilmiş olabilir)")
    m = _GOVDE.search(govde)
    if not m:
        eksik = [e for e in ("<kart>", "<sol>", "<sag>") if e not in govde]
        if govde.count("<sonuc>") < 2:
            eksik.append("<sonuc> (iki tane olmalı)")
        raise KartBicimHatasi("etiketler eksik ya da sırası yanlış: " + (", ".join(eksik) or "<kart> <sol> <sonuc> <sag> <sonuc> </kart> sırası bozuk"))
    kart_metni = m.group(1).strip()
    if not kart_metni:
        raise KartBicimHatasi("<kart> metni boş")
    kart = {"metin": kart_metni,
            "sol": _secenek_oku("sol", m.group(2), m.group(3)),
            "sag": _secenek_oku("sag", m.group(4), m.group(5))}
    malzeme = {"karakter": karakter, "durum": durum, "ekstra": {"konu": konu}}
    return kart, malzeme


# ---------- öğretmenin satırlı çıktısı -> kart ----------

_SATIR = {"metin": "metin", "sol": "sol.karar", "sol sonuç": "sol.sonuc", "sol etki": "sol.etki",
          "sağ": "sag.karar", "sağ sonuç": "sag.sonuc", "sağ etki": "sag.etki"}


def _etki_oku(ad, yazi):
    """"Halk ++, Para -" -> {"halk": 10, "para": -5}."""
    etki = {}
    for parca in yazi.split(","):
        m = re.fullmatch(r"\s*(\S+)\s*([+-]{1,3})\s*", parca)
        if not m or m.group(1) not in GOSTERGELER or m.group(2) not in ETKI_KADEMELERI:
            raise KartBicimHatasi(f"{ad}: geçersiz etki {parca.strip()!r}")
        if GOSTERGELER[m.group(1)] in etki:
            raise KartBicimHatasi(f"{ad}: {m.group(1)} iki kez yazılmış")
        etki[GOSTERGELER[m.group(1)]] = ETKI_KADEMELERI[m.group(2)]
    return etki


def satirli_karta(cikti):
    """Filtreden geçmiş satırlı kart -> kart sözlüğü. Eksik satır ya da bozuk etkide KartBicimHatasi."""
    alan = {}
    for satir in cikti.splitlines():
        ad, ayrac, deger = satir.partition(":")
        if ayrac and _kucuk(ad.strip()) in _SATIR and deger.strip():
            alan[_SATIR[_kucuk(ad.strip())]] = deger.strip()
    eksik = [a for a in _SATIR.values() if a not in alan]
    if eksik:
        raise KartBicimHatasi(f"eksik satır: {', '.join(eksik)}")
    def taraf(t):
        return {"karar": alan[f"{t}.karar"], "sonuc": alan[f"{t}.sonuc"], "etki": _etki_oku(t, alan[f"{t}.etki"])}
    return {"metin": alan["metin"], "sol": taraf("sol"), "sag": taraf("sag")}


def main():
    ap = argparse.ArgumentParser(description="Temiz jsonl'deki kartları etiketli eğitim metnine çevirir (aralarında boş satır).")
    ap.add_argument("girdi")
    ap.add_argument("cikti")
    a = ap.parse_args()
    yazilan, atilan = 0, 0
    with open(a.girdi, encoding="utf-8") as g, open(a.cikti, "w", encoding="utf-8") as c:
        for satir in g:
            k = json.loads(satir)
            if k.get("tur") != "kart":
                continue
            try:
                c.write(egitim_metni(satirli_karta(k["cikti"]), k["malzeme"]) + "\n\n")
                yazilan += 1
            except (KartBicimHatasi, KeyError, ValueError) as e:
                atilan += 1
                print(f"atlandı {k.get('id')}: {e}")
    print(f"{yazilan} kart yazıldı, {atilan} atlandı: {a.cikti}")


if __name__ == "__main__":
    main()
