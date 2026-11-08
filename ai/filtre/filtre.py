#!/usr/bin/env python3
"""S1 filtresi: ham üretimi temizler ve hangi kuraldan kaç kaydın atıldığını raporlar. Girdiler değiştirilmez.

    python ai/filtre/filtre.py ~/Downloads/kaydir_veri               # çıktı: <veri>/filtre/
    python ai/filtre/filtre.py ~/Downloads/kaydir_veri --cikti /tmp/f
    python ai/filtre/filtre.py ~/Downloads/kaydir_veri --kelimeye-bakma   # verilen kelime kuralı kapalı

Girdi : <veri>/ham/*.jsonl (her satırda malzeme ve cikti)
Çıktı : filtre/temiz/<dosya>.jsonl   geçen kayıtlar; kartta "kart" alanı S2'nin okuduğu sözlüktür
        filtre/elenen/<dosya>.jsonl  atılan kayıtlar ve sebepleri
        filtre/rapor.md, rapor.json  kural başına atılan kayıt sayısı (prompt bu sayılarla düzeltilir)

Biçim çözme, sınırlar (kart 20–50 / karar 2–5, hikâye 90–150) ve prompt kuralları duzenle.py'den gelir,
böylece iki betik aynı kartı aynı şekilde okur. Filtre bunların üstüne yz_gorevleri.md S1'deki kuralları ekler:
boş çıktı, bozuk kelime (ünlü uyumu), modern kelime ve verilen kelimelerin metinde geçmesi.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import duzenle  # noqa: E402
from ai.ortak.ayarlar import TEMA_DOSYASI  # noqa: E402
from ai.ortak.kart_bicimi import KartBicimHatasi, satirli_karta  # noqa: E402

BOS_CIKTI = "[BOŞ ÇIKTI]"
YASAK_KELIMELER = tuple(json.loads(Path(TEMA_DOSYASI).read_text(encoding="utf-8"))["yasak_kelimeler"])

KALIN, INCE = set("aıou"), set("eiöü")
UNLULER = KALIN | INCE | set("âîû")   # â î û iki yöne de gidebilir: bu ünlüden sonra uyum denetlenmez

# Son hecesi kalın olduğu halde ince ek alan alıntı kökler (saatler, kalbi, hali). Gerçek veride yanlış alarm
# verenler ve sık görülen benzerleri; "-aat" ile bitenler (cemaat, itaat) ayrıca kabul edilir.
INCE_EK_ALAN = {
    "alp", "alkol", "celal", "cemal", "dikkat", "emsal", "gol", "hakikat", "hal", "harf", "harp", "hayal",
    "hilal", "idrak", "ihlal", "ihmal", "ihtimal", "istiklal", "kabul", "kalp", "kemal", "kontrol", "kristal",
    "meal", "meşgul", "metal", "mineral", "misal", "moral", "muhal", "rol", "saat", "sadakat", "seyahat",
    "sinyal", "sual", "usul",
}

# taş + leri: kökün son ünlüsü ile çoğul ekinin ünlüsü uyuşmuyor
COGUL_RE = re.compile(
    r"^(.{2,}?)(lar|ler)((?:[ıiuü]|[ıiuü]n|[ıiuü]n[ıiuü]n|d[ae]n?|[ae]|[ıiuü]m[ıiuü]z|[ıiuü]n[ıiuü]z"
    r"|[ıiuü]n[ae]|[ıiuü]nd[ae]n?)?)$"
)
# halk + ı + nin: ekin kendi içinde ünlüsü uyuşmuyor (iyelik ünlüsünden sonra ilgi ya da bulunma/çıkma eki).
# "-na/-ne" bilerek yok: karantina, makina gibi köklerde yanlış alarm veriyordu.
EK_ICI_RE = re.compile(r"([ıiuü])(n[ıiuü]n|nd[ae]n?)$")

SEBEPLER = dict(duzenle.SEBEPLER)
SEBEPLER.update({
    "bos_cikti": "Model çıktı üretemedi ([BOŞ ÇIKTI]).",
    "bozuk_kelime": "Ünlü uyumu bozuk kelime var (taşleri, halkınin).",
    "modern_kelime": "Modern kelime var (tema.json yasak_kelimeler).",
    "kelime_gecmiyor": "Verilen kelimeler geçmiyor (kartta ikisinden en az biri, hikâyede üçü de gerekli).",
})


def _sinif(unlu):
    return "kalin" if unlu in KALIN else "ince" if unlu in INCE else None


def _son_unlu(s):
    return next((c for c in reversed(s) if c in UNLULER), None)


def bozuk_mu(kelime):
    """Küçük harfli tek kelime ünlü uyumunu bozuyor mu. "arkadaşinin" gibi doğru yazılışla aynı olan hatalar yakalanamaz."""
    m = COGUL_RE.match(kelime)
    if m:
        kok, ek = m.group(1), m.group(2)
        kok_sinif = _sinif(_son_unlu(kok) or "")
        istisna = kok in INCE_EK_ALAN or kok.endswith("aat")
        if kok_sinif and not istisna and kok_sinif != ("kalin" if ek == "lar" else "ince"):
            return True
    m = EK_ICI_RE.search(kelime)
    if m and len(kelime) > len(m.group(0)) + 1:
        ek_unlusu = next(c for c in m.group(2) if c in UNLULER)
        if _sinif(m.group(1)) != _sinif(ek_unlusu):
            return True
    return False


def kelimeler(metin):
    return re.findall(r"[a-zçğıöşüâîû]+", duzenle._kucuk(metin))


def bozuk_kelimeler(metin):
    return sorted({k for k in kelimeler(metin) if bozuk_mu(k)})


def modern_kelimeler(metin):
    """Kısa yasak kelime yalnızca tam kelime olarak aranır; 6+ harfli olanın ek almış hali de yakalanır (politikası)."""
    return sorted({k for k in kelimeler(metin) for y in YASAK_KELIMELER if k == y or (len(y) >= 6 and k.startswith(y))})


def kelime_gecmiyor(tur, metin, malzeme):
    kucuk = duzenle._kucuk(metin)
    gecen = [k for k in malzeme.get("kelimeler", []) if duzenle._geciyor(k, kucuk)]
    if not malzeme.get("kelimeler"):
        return False
    return not gecen if tur == "kart" else len(gecen) < len(malzeme["kelimeler"])


def _yazi(tur, cikti):
    """Kelime kurallarının bakacağı metin: kartta etiketler ve etki satırları dışarıda kalır."""
    if tur == "hikaye":
        return cikti
    alan = dict(satir.split(": ", 1) for satir in cikti.split("\n"))
    return " ".join(alan[a] for a in ("Metin", "Sol", "Sol sonuç", "Sağ", "Sağ sonuç"))


def kayit_sorunlari(r, kelime_kontrolu=True):
    """(temiz cikti, ayrıştırılmış kart ya da None, sebep kodları, ayrıntı) döner. Tekrar kontrolü burada değil."""
    tur, ham = r["tur"], r.get("cikti") or ""
    if not ham.strip() or ham.strip() == BOS_CIKTI:
        return None, None, ["bos_cikti"], {}
    cikti, _, sorun = (duzenle.kart_coz if tur == "kart" else duzenle.hikaye_coz)(ham)
    if sorun:
        return cikti, None, sorun, {}
    malzeme = r.get("malzeme") or {}
    sorun = list(duzenle.icerik_sorunlari(tur, cikti, malzeme))
    yazi = _yazi(tur, cikti)
    ayrinti = {}
    bozuk = bozuk_kelimeler(yazi)
    if bozuk:
        sorun.append("bozuk_kelime")
        ayrinti["bozuk"] = bozuk
    modern = modern_kelimeler(yazi)
    if modern:
        sorun.append("modern_kelime")
        ayrinti["modern"] = modern
    if kelime_kontrolu and kelime_gecmiyor(tur, yazi, malzeme):
        sorun.append("kelime_gecmiyor")
    kart = None
    if tur == "kart" and not sorun:
        try:
            kart = satirli_karta(cikti)
        except KartBicimHatasi:
            sorun.append("gecersiz_etki")
    return cikti, kart, sorted(set(sorun)), ayrinti


def filtrele(veri, cikti_klasoru, kelime_kontrolu=True):
    temiz_dir, elenen_dir = cikti_klasoru / "temiz", cikti_klasoru / "elenen"
    temiz_dir.mkdir(parents=True, exist_ok=True)
    elenen_dir.mkdir(parents=True, exist_ok=True)
    sebep = collections.Counter()           # her sebep kaç kayıtta görüldü
    tek_sebep = collections.Counter()       # yalnızca bu sebeple atılan kayıt sayısı
    dosya_say = {}
    ornek = collections.defaultdict(collections.Counter)   # bozuk ve modern kelimelerin en sıkları
    gorulen_cikti, gorulen_prompt, gorulen_metin = set(), set(), set()

    yollar = sorted(glob.glob(str(veri / "ham" / "*.jsonl")))
    if not yollar:
        raise SystemExit(f"{veri / 'ham'} içinde .jsonl yok")
    for yol in yollar:
        ad = os.path.basename(yol)
        say = collections.Counter()
        with open(yol, encoding="utf-8") as g, \
                open(temiz_dir / ad, "w", encoding="utf-8") as t, \
                open(elenen_dir / ad, "w", encoding="utf-8") as e:
            for satir in g:
                if not satir.strip():
                    continue
                r = json.loads(satir)
                cikti, kart, sorun, ayrinti = kayit_sorunlari(r, kelime_kontrolu)
                if not sorun and cikti in gorulen_cikti:
                    sorun = ["mukerrer"]
                if not sorun and r.get("prompt") and r["prompt"] in gorulen_prompt:
                    sorun = ["ayni_prompt"]
                if not sorun and r["tur"] == "kart" and cikti.split("\n", 1)[0] in gorulen_metin:
                    sorun = ["ayni_metin"]
                say[r["tur"] + "_toplam"] += 1
                kaynak_id = f"{ad}#{r.get('id')}"
                if sorun:
                    sebep.update(sorun)
                    if len(sorun) == 1:
                        tek_sebep[sorun[0]] += 1
                    for tur_adi, liste in ayrinti.items():
                        ornek[tur_adi].update(liste)
                    e.write(json.dumps({"kaynak_id": kaynak_id, "tur": r["tur"], "sebep_kodu": sorun,
                                        "sebep": [_sebep_yazi(k) for k in sorun],
                                        **ayrinti, "malzeme": r.get("malzeme"), "cikti": r.get("cikti")},
                                       ensure_ascii=False) + "\n")
                    continue
                gorulen_cikti.add(cikti)
                if r.get("prompt"):
                    gorulen_prompt.add(r["prompt"])
                if r["tur"] == "kart":
                    gorulen_metin.add(cikti.split("\n", 1)[0])
                say[r["tur"] + "_temiz"] += 1
                temiz = {k: r.get(k) for k in ("id", "tur", "malzeme", "prompt", "model", "motor", "tohum")}
                temiz.update({"kaynak_id": kaynak_id, "cikti": cikti})
                if kart is not None:
                    temiz["kart"] = kart
                t.write(json.dumps(temiz, ensure_ascii=False) + "\n")
        dosya_say[ad] = dict(say)
    rapor = {"dosyalar": dosya_say, "sebep": dict(sebep.most_common()), "tek_sebep": dict(tek_sebep.most_common()),
             "en_sik_bozuk": dict(ornek["bozuk"].most_common(20)), "en_sik_modern": dict(ornek["modern"].most_common(20))}
    (cikti_klasoru / "rapor.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
    (cikti_klasoru / "rapor.md").write_text(rapor_md(rapor), encoding="utf-8")
    return rapor


def _sebep_yazi(kod):
    return SEBEPLER.get(kod) or duzenle.sebep_yazi(kod)


def rapor_md(rapor):
    toplam = collections.Counter()
    for say in rapor["dosyalar"].values():
        toplam.update(say)
    satirlar = ["# Filtre raporu", "", "| Tür | Toplam | Geçen | Oran |", "|---|---:|---:|---:|"]
    for tur in ("kart", "hikaye"):
        n, ok = toplam[tur + "_toplam"], toplam[tur + "_temiz"]
        if n:
            satirlar.append(f"| {tur} | {n} | {ok} | %{100 * ok / n:.1f} |")
    satirlar += ["", "## Hangi kuraldan kaç kayıt atıldı", "",
                 "Bir kayıt birden çok kurala takılabilir; \"yalnız bu\" sütunu tek sebeple atılanlardır.", "",
                 "| Kural | Kayıt | Yalnız bu | Açıklama |", "|---|---:|---:|---|"]
    for kod, n in rapor["sebep"].items():
        satirlar.append(f"| `{kod}` | {n} | {rapor['tek_sebep'].get(kod, 0)} | {_sebep_yazi(kod)} |")
    for baslik, anahtar in (("En sık bozuk kelimeler", "en_sik_bozuk"), ("En sık modern kelimeler", "en_sik_modern")):
        if rapor[anahtar]:
            satirlar += ["", f"## {baslik}", "", ", ".join(f"{k} ({n})" for k, n in rapor[anahtar].items())]
    satirlar += ["", "## Dosya başına", "", "| Dosya | Kart | Geçen | Hikâye | Geçen |", "|---|---:|---:|---:|---:|"]
    for ad, say in rapor["dosyalar"].items():
        satirlar.append(f"| {ad} | {say.get('kart_toplam', 0)} | {say.get('kart_temiz', 0)} | "
                        f"{say.get('hikaye_toplam', 0)} | {say.get('hikaye_temiz', 0)} |")
    return "\n".join(satirlar) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Ham üretimi S1 kurallarıyla filtreler ve eleme raporu yazar.")
    ap.add_argument("veri", help="ham/ klasörünü içeren veri klasörü")
    ap.add_argument("--cikti", help="çıktı klasörü (varsayılan: <veri>/filtre)")
    ap.add_argument("--kelimeye-bakma", action="store_true",
                    help="verilen kelimelerin geçip geçmediğine bakma (duzenle.py gibi; kural toplantıda kesinleşecek)")
    a = ap.parse_args()
    veri = Path(a.veri).expanduser().resolve()
    cikti = Path(a.cikti).expanduser().resolve() if a.cikti else veri / "filtre"
    rapor = filtrele(veri, cikti, kelime_kontrolu=not a.kelimeye_bakma)
    print(rapor_md(rapor))
    print(f"Yazıldı: {cikti}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
