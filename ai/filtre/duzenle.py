#!/usr/bin/env python3
"""ham/ ve altin/ klasörlerindeki dosyaları temiz/ altında tek formata çevirir. Girdiler değiştirilmez.

    python ai/filtre/duzenle.py ~/Downloads/kaydir_veri

Veri klasörü verilmezse betiğin bulunduğu klasör kullanılır. Bugüne kadarki temiz verinin hepsi bu betikten geçti;
S1 filtresi (`filtre.py`) gelene kadar geçerli olan temizlik budur. Sınırlar için bkz. kararlar.md 7 Kasım.

Girdi : ham/*.jsonl (model çıktıları), altin/*.txt (altın set kartları)
Çıktı : temiz/model_ciktilari.jsonl (biçim, oyun sınırı ve içerik kurallarından geçen tüm model kayıtları;
        modern ya da verilen kelime elenmez), temiz/altin_set.jsonl (kurallardan geçen altın kartlar),
        silindi/model_silinenler.jsonl, silindi/altin_silinenler.jsonl (elenenler ve silinme sebepleri)
"""
import collections
import glob
import json
import os
import re
import sys
import unicodedata

KOK = os.path.abspath(os.path.expanduser(sys.argv[1])) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "ham")
ALTIN = os.path.join(KOK, "altin")
TEMIZ = os.path.join(KOK, "temiz")
SILINDI = os.path.join(KOK, "silindi")

HIKAYE_MIN, HIKAYE_MAX = 90, 150
KART_METIN_PROMPT_MAX = 35
METIN_MIN, METIN_MAX = 20, 50
KARAR_MIN, KARAR_MAX = 2, 5
ALANLAR = ["Metin", "Sol", "Sol sonuç", "Sol etki", "Sağ", "Sağ sonuç", "Sağ etki"]

ETIKET_RE = re.compile(
    r"^(Metin|Sol sonu[çc]u?|Sağ sonu[çc]u?|Sol etki|Sağ etki|Sol down|Sol|Sağ)\s*:\s*(.*)$"
)
ETKI_RE = re.compile(r"^(Yönetim|Halk|Para|Ordu)\s*(\+{1,3}|-{1,3})$")
SON_NOKTALAMA = ('.', '!', '?', '"', "'", ')', '}')

# Altın set: başlık satırı ve altin_set_uretici.html'deki doğrulama kuralları
BASLIK_RE = re.compile(r"^KART (\d+) · Konuşan: (.+?) · Durum: (.+?) · Kelimeler: (.+?)(?: · (.*))?$")
EKSTRA_ALAN = {"Konu": "konu", "Olay": "olay", "Yer": "yer", "Zaman": "zaman", "Ruh hâli": "ruh",
               "İkilem": "ikilem", "Özellik": "ozellik", "Anlatım": "uslup"}
HITAP_YASAK = {"beyim", "hatunum", "hünkârım", "hünkarım", "sultanım", "efendim", "padişahım",
               "beyefendi", "hanımefendi", "hakanım", "kralım"}
MODERN_YASAK = ("bakan", "bütçe", "depo", "ekonomi", "garnizon", "güvenlik", "lüks", "meclis", "memur", "müzakere",
                "politika", "proje", "reform", "rezervuar", "sistem", "telefon", "temsilci", "tesisat", "vali")


SEBEPLER = {
    "ayni_prompt": "Aynı prompt daha önce geçti; her prompttan tek kayıt tutuluyor (Colab aynı tohumla baştan çalışmış).",
    "ayni_metin": "Aynı kart metni daha önce geçti.",
    "mukerrer": "Birebir aynı çıktı daha önce geçti.",
    "bos_alan": "Çıktı ya da alanlardan biri boş.",
    "yarim_kalmis": "Metin yarım kalmış; model çoğunlukla tekrara girip token sınırına dayanmış.",
    "yabanci_harf": "Türkçe metnin içinde Latin dışı harf var.",
    "gecersiz_etki": "Etki satırı geçersiz: olmayan gösterge, aynı göstergenin iki kez yazılması ya da bozuk biçim.",
    "etiketsiz_satir": "Çıktıda etiketsiz satır var, kart çözülemedi.",
    "karar_satiri_yanlis": "Sol/Sağ karar satırları yanlış sırada.",
    "alan_yerine_etki": "Metin ya da karar alanında etki yazıyor.",
    f"metin<{METIN_MIN}": f"Oyun sınırı: kart metni {METIN_MIN} kelimeden kısa.",
    f"metin>{METIN_MAX}": f"Oyun sınırı: kart metni {METIN_MAX} kelimeden uzun.",
    f"karar<{KARAR_MIN}": f"Oyun sınırı: karar {KARAR_MIN} kelimeden kısa.",
    f"karar>{KARAR_MAX}": f"Oyun sınırı: karar {KARAR_MAX} kelimeden uzun.",
    f"metin>{KART_METIN_PROMPT_MAX}": f"Prompt kuralı: kart metni {KART_METIN_PROMPT_MAX} kelimeden uzun.",
    f"hikaye<{HIKAYE_MIN}": f"Hikâye {HIKAYE_MIN} kelimeden kısa.",
    f"hikaye>{HIKAYE_MAX}": f"Hikâye {HIKAYE_MAX} kelimeden uzun.",
    "karakter_gecmiyor": "Verilen karakter hikâyede geçmiyor (tahmini kontrol).",
    "kararda_dusus_yok": "Prompt kuralı: kararlardan birinde hiçbir gösterge düşmüyor.",
    "gosterge_dusurmuyor": "Prompt kuralı: kararlardan birinde hiçbir gösterge düşmüyor.",
    "etki>3_gosterge": "Prompt kuralı: bir karar 3'ten fazla göstergeyi etkiliyor.",
    "iki_secenek_ayni": "İki karar ya da iki sonuç aynı.",
    "uydurma_yer_tutucu": "Metinde {hitap} dışında uydurma yer tutucu var.",
    "yasak_hitap": "Prompt kuralı: {hitap} yerine elle hitap yazılmış (Beyim, Hünkârım gibi).",
    "hitap_elle_yazilmis": "Prompt kuralı: {hitap} yerine elle hitap yazılmış (Beyim, Hünkârım gibi).",
    "modern_kelime": "Altın set kuralı: modern kelime var.",
}


def sebep_yazi(kod):
    m = re.fullmatch(r"alan_sayisi_(\d+)", kod)
    if m:
        return f"Kart 7 satır olmalı, {m.group(1)} satır çıktı."
    return SEBEPLER[kod]


def yabanci_harf(s):
    """Latin dışı harf var mı (Çince, Hangul, Bengalce, Kiril...)."""
    return any(c.isalpha() and not unicodedata.name(c, "?").startswith("LATIN") for c in s)


def duz(s):
    """Tüm kaynaklarda aynı yazım: NFC, düz tırnak, işaretleme yok."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\\", "").replace("**", "")
    for eski, yeni in (("“", '"'), ("”", '"'), ("‘", "'"), ("’", "'")):
        s = s.replace(eski, yeni)
    return s


def bosluk(s):
    return re.sub(r"\s+", " ", s).strip()


def etki_duzelt(deger):
    """'Ordu - , Yönetim -' -> 'Ordu -, Yönetim -'. Geçersizse None."""
    parcalar = []
    for p in deger.split(","):
        m = ETKI_RE.match(p.strip())
        if not m:
            return None
        parcalar.append(f"{m.group(1)} {m.group(2)}")
    adlar = [p.split()[0] for p in parcalar]
    if not parcalar or len(adlar) != len(set(adlar)):
        return None
    return ", ".join(parcalar)


def kart_coz(metin):
    """Kart metnini 7 alana çözer. (kanonik_metin, duzeltmeler, sorunlar) döner."""
    duzeltme, sorun = [], []
    satirlar = [l.strip() for l in duz(metin).split("\n") if l.strip()]

    # Baştaki liste işaretleri, numara ve gövdeye yapışmış model çöpleri
    temiz = []
    for l in satirlar:
        y = re.sub(r"^(?:[-*•]\s+|\d+\.\s+)", "", l)
        y = re.sub(r"^[一-鿿_]+(?=Metin\s*:)", "", y)
        if y != l:
            duzeltme.append("onek_silindi")
        temiz.append(y)
    satirlar = temiz

    # "Metin:" satırından önceki her şey giriş cümlesidir
    i_metin = next((i for i, l in enumerate(satirlar) if re.match(r"Metin\s*:", l)), None)
    if i_metin:
        satirlar = satirlar[i_metin:]
        duzeltme.append("giris_silindi")

    # Etiketsiz ilk satır: Metin'dir ("Ahi Ustası: ..." gibi konuşan öneki atılır)
    if i_metin is None and satirlar and not ETIKET_RE.match(satirlar[0]):
        ilk = re.sub(r"^[^:.!?]{1,20}:\s+", "", satirlar[0])
        satirlar[0] = "Metin: " + ilk
        duzeltme.append("metin_etiketi_eklendi")

    alanlar = []
    for l in satirlar:
        m = ETIKET_RE.match(l)
        if m:
            alanlar.append([m.group(1), bosluk(m.group(2))])
        elif re.match(r"^(?:Sol|Sağ)$|^Solষম |^Sol (?:undeveloped|empty)$", l):
            duzeltme.append("cop_satir_silindi")
        elif alanlar:
            alanlar[-1][1] = bosluk(alanlar[-1][1] + " " + l)
            duzeltme.append("kirik_satir_birlesti")
        else:
            sorun.append("etiketsiz_satir")

    # Birebir tekrar eden ardışık satırlar (etki satırının sonuç etiketiyle tekrarı dahil)
    tekil = []
    for a in alanlar:
        if tekil and tekil[-1][1].replace(" ,", ",") == a[1].replace(" ,", ","):
            duzeltme.append("tekrar_satir_silindi")
            continue
        tekil.append(a)
    alanlar = tekil

    if len(alanlar) != 7:
        return None, duzeltme, sorun + [f"alan_sayisi_{len(alanlar)}"]

    # 7 satır sırası doğruysa yanlış etiket konumdan düzeltilir ("Sol sonuç" -> "Sağ sonuç")
    if alanlar[1][0] != "Sol" or alanlar[4][0] != "Sağ":
        sorun.append("karar_satiri_yanlis")
    degerler = {}
    for ad, (etiket, deger) in zip(ALANLAR, alanlar):
        if etiket != ad:
            duzeltme.append("etiket_duzeltildi")
        degerler[ad] = deger

    for ad in ("Sol etki", "Sağ etki"):
        e = etki_duzelt(degerler[ad])
        if e is None:
            sorun.append("gecersiz_etki")
        else:
            degerler[ad] = e
    for ad in ("Metin", "Sol", "Sol sonuç", "Sağ", "Sağ sonuç"):
        if not degerler[ad]:
            sorun.append("bos_alan")
        elif ETKI_RE.match(degerler[ad].split(",")[0].strip()):
            sorun.append("alan_yerine_etki")
    for ad in ("Metin", "Sol sonuç", "Sağ sonuç"):
        if degerler[ad] and not degerler[ad].endswith(SON_NOKTALAMA):
            sorun.append("yarim_kalmis")
    if yabanci_harf(" ".join(degerler.values())):
        sorun.append("yabanci_harf")

    # Oyunun Kart.cs sınırları: dışında kalan tek kart bile desteyi düşürür
    metin_kelime = len(degerler["Metin"].split())
    if metin_kelime < METIN_MIN:
        sorun.append(f"metin<{METIN_MIN}")
    elif metin_kelime > METIN_MAX:
        sorun.append(f"metin>{METIN_MAX}")
    for ad in ("Sol", "Sağ"):
        karar_kelime = len(degerler[ad].split())
        if karar_kelime < KARAR_MIN:
            sorun.append(f"karar<{KARAR_MIN}")
        elif karar_kelime > KARAR_MAX:
            sorun.append(f"karar>{KARAR_MAX}")

    return "\n".join(f"{a}: {degerler[a]}" for a in ALANLAR), duzeltme, sorted(set(sorun))


def hikaye_coz(metin):
    """Hikâyeyi başlıksız, tek paragraf düz metne çevirir."""
    duzeltme, sorun = [], []
    s = duz(metin).strip()

    y = re.sub(r"^[^\w\"']*(?:[一-鿿_]*)\s*thought\s*\n", "", s)
    if y != s:
        duzeltme.append("thought_silindi")
    s = y.strip()

    # Baştaki başlık (kısa ve noktalamasız ilk satır)
    parcalar = [p.strip() for p in s.split("\n") if p.strip()]
    while len(parcalar) > 1 and len(parcalar[0].split()) <= 8 and not parcalar[0].endswith((*SON_NOKTALAMA, ":")):
        parcalar.pop(0)
        duzeltme.append("baslik_silindi")
    # Sondaki tek karakterlik model çöpü ("-", "--")
    while parcalar and re.fullmatch(r"[-–—*_.]+", parcalar[-1]):
        parcalar.pop()
        duzeltme.append("son_cop_silindi")
    if len(parcalar) > 1:
        duzeltme.append("paragraflar_birlesti")
    s = bosluk(" ".join(parcalar))

    if not s:
        sorun.append("bos_alan")
    elif not s.endswith(SON_NOKTALAMA):
        sorun.append("yarim_kalmis")
    if yabanci_harf(s):
        sorun.append("yabanci_harf")
    return s, duzeltme, sorted(set(sorun))


def kayit(sayac, set_adi, tur, kaynak, kaynak_id, malzeme, cikti, kaynak_satir=None):
    sayac[(set_adi, tur)] += 1
    r = {
        "surum": 3,
        "id": f"{set_adi}-{tur}-{sayac[(set_adi, tur)]:06d}",
        "set": set_adi,
        "tur": tur,
        "kaynak": kaynak,
        "kaynak_id": kaynak_id,
        "malzeme": malzeme,
        "prompt": None,
        "cikti": cikti,
        "model": None,
        "motor": None,
        "tohum": None,
        "token": None,
        "saniye": None,
    }
    if kaynak_satir:
        r.update({k: kaynak_satir.get(k) for k in ("prompt", "model", "motor", "tohum", "token", "saniye")})
    return r


def silinenleri_yaz(ad, satirlar):
    os.makedirs(SILINDI, exist_ok=True)
    with open(os.path.join(SILINDI, ad), "w", encoding="utf8") as f:
        for r in satirlar:
            f.write(json.dumps({
                "kaynak": r["kaynak"],
                "kaynak_id": r["kaynak_id"],
                "tur": r["tur"],
                "silinme_sebebi": [sebep_yazi(k) for k in r["sorunlar"]],
                "sebep_kodu": r["sorunlar"],
                "malzeme": r["malzeme"],
                "prompt": r["prompt"],
                "cikti": r["ham"],
            }, ensure_ascii=False) + "\n")


def yaz(ad, satirlar):
    with open(os.path.join(TEMIZ, ad), "w", encoding="utf8") as f:
        for r in satirlar:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _kucuk(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def _geciyor(kelime, kucuk_metin):
    """Kök eşleştirmesi; ek alınca değişen kökleri de arar (vakit/vakti, kalp/kalbi, ocak/ocağı). Tahminidir."""
    kok = re.sub(r"(mek|mak)$", "", _kucuk(kelime))
    kokler = {kok[:-1] if len(kok) >= 5 else kok}
    if len(kok) >= 3 and kok[-1] in "kçtp":
        kokler.add(kok[:-1] + {"k": "ğ", "ç": "c", "t": "d", "p": "b"}[kok[-1]])
    if len(kok) >= 4 and kok[-2] in "aeıioöuü" and kok[-3] not in "aeıioöuü":
        kokler.add(kok[:-2] + kok[-1])
    return any(re.search(r"(?<!\w)" + re.escape(k), kucuk_metin) for k in kokler)


def icerik_sorunlari(tur, cikti, malzeme):
    """Prompt kuralları. Modern kelime ve verilen kelimeler (yalnızca çeşitlilik için) bilerek kontrol edilmez."""
    sorun = []
    if tur == "hikaye":
        kelime = len(cikti.split())
        if kelime < HIKAYE_MIN:
            sorun.append(f"hikaye<{HIKAYE_MIN}")
        elif kelime > HIKAYE_MAX:
            sorun.append(f"hikaye>{HIKAYE_MAX}")
        kucuk = _kucuk(cikti)
        if not _geciyor(malzeme["karakter"].split()[0], kucuk):
            sorun.append("karakter_gecmiyor")
        return sorun
    alan = dict(l.split(": ", 1) for l in cikti.split("\n"))
    if len(alan["Metin"].split()) > KART_METIN_PROMPT_MAX:
        sorun.append(f"metin>{KART_METIN_PROMPT_MAX}")
    for ad in ("Sol etki", "Sağ etki"):
        if "-" not in alan[ad]:
            sorun.append("kararda_dusus_yok")
        if len(alan[ad].split(",")) > 3:
            sorun.append("etki>3_gosterge")
    if _kucuk(alan["Sol"]) == _kucuk(alan["Sağ"]) or alan["Sol sonuç"] == alan["Sağ sonuç"]:
        sorun.append("iki_secenek_ayni")
    if re.search(r"\{(?!hitap\})", cikti):
        sorun.append("uydurma_yer_tutucu")
    if HITAP_YASAK & set(re.findall(r"[a-zçğıöşüâîû]+", _kucuk(cikti))):
        sorun.append("yasak_hitap")
    return sorted(set(sorun))


def model_isle(sayac, rapor):
    temiz, sorunlu, gorulen = [], [], {}
    gorulen_metin, gorulen_prompt = set(), set()
    for yol in sorted(glob.glob(os.path.join(HAM, "*.jsonl"))):
        dosya = os.path.basename(yol)
        with open(yol, encoding="utf8") as f:
            for satir in f:
                r = json.loads(satir)
                tur = r["tur"]
                cikti, duz_list, sorun = (kart_coz if tur == "kart" else hikaye_coz)(r["cikti"])
                malzeme = dict(r["malzeme"])
                if not sorun:
                    sorun = icerik_sorunlari(tur, cikti, malzeme)
                if not sorun and cikti in gorulen:
                    sorun = ["mukerrer"]
                if not sorun and r["prompt"] in gorulen_prompt:
                    sorun = ["ayni_prompt"]  # Colab aynı tohumla baştan çalışınca tekrar eder; ilk geçen kayıt kalır
                if not sorun and tur == "kart":
                    metin_satiri = cikti.split("\n", 1)[0]
                    if metin_satiri in gorulen_metin:
                        sorun = ["ayni_metin"]
                    gorulen_metin.add(metin_satiri)
                kaynak_id = f"{dosya}#{r['id']}"
                rapor[("model", dosya, tur)]["toplam"] += 1
                for d in set(duz_list):
                    rapor[("model", dosya, tur)]["duzeltme:" + d] += 1
                if sorun:
                    for x in sorun:
                        rapor[("model", dosya, tur)]["sorun:" + x] += 1
                    sorunlu.append({"kaynak": dosya, "kaynak_id": kaynak_id, "tur": tur, "sorunlar": sorted(set(sorun)), "malzeme": malzeme, "prompt": r["prompt"], "ham": r["cikti"]})
                    continue
                gorulen[cikti] = kaynak_id
                gorulen_prompt.add(r["prompt"])
                rapor[("model", dosya, tur)]["temiz"] += 1
                temiz.append(kayit(sayac, "model", tur, dosya, kaynak_id, malzeme, cikti, r))
    return temiz, sorunlu


def malzeme_coz(baslik, yol):
    """'KART n · Konuşan: … · Durum: … · Kelimeler: … · Konu: …' satırını (no, malzeme) olarak çözer."""
    m = BASLIK_RE.match(baslik)
    if not m:
        raise ValueError(f"{yol}: başlık çözülemedi: {baslik}")
    durum = {ad: int(deger) for ad, deger in (p.split() for p in m.group(3).split(", "))}
    ekstra = {}
    for parca in (m.group(5) or "").split(" · "):
        if parca:
            ad, deger = parca.split(": ", 1)
            ekstra[EKSTRA_ALAN[ad]] = "serbest" if ad == "Konu" and deger.startswith("serbest") else deger
    return int(m.group(1)), {"tur": "kart", "karakter": m.group(2), "kelimeler": m.group(4).split(", "), "ekstra": ekstra, "durum": durum}


def hitap_duzelt(govde):
    """'Metin: Beyim, ...' -> 'Metin: {hitap}, ...'. Başka konumdaki hitap altin_sorunlari'nda yakalanır."""
    return re.sub(r"^Metin: (?:Beyim|Hünkârım),", "Metin: {hitap},", govde, count=1, flags=re.M)


def altin_sorunlari(cikti):
    """Üreticinin kart_coz dışında kalan kuralları: elle hitap, modern kelime, düşürmeyen seçenek."""
    sorun = []
    alan = dict(l.split(": ", 1) for l in cikti.split("\n"))
    yazi = " ".join(alan[a] for a in ("Metin", "Sol", "Sol sonuç", "Sağ", "Sağ sonuç"))
    kucuk = yazi.replace("I", "ı").replace("İ", "i").lower()
    tokenler = re.findall(r"[a-zçğıöşüâîû]+", kucuk)
    if HITAP_YASAK & set(tokenler):
        sorun.append("hitap_elle_yazilmis")
    if any(t == y or (len(y) >= 6 and t.startswith(y)) for t in tokenler for y in MODERN_YASAK):
        sorun.append("modern_kelime")
    for ad in ("Sol etki", "Sağ etki"):
        if "-" not in alan[ad]:
            sorun.append("gosterge_dusurmuyor")
    return sorun


def altin_isle(sayac, rapor):
    temiz, sorunlu, gorulen = [], [], {}
    for yol in sorted(glob.glob(os.path.join(ALTIN, "*.txt"))):
        dosya = os.path.basename(yol)
        with open(yol, encoding="utf8") as f:
            bloklar = re.split(r"\n\s*\n", f.read().strip())
        for blok in bloklar:
            baslik, _, govde = blok.partition("\n")
            no, malzeme = malzeme_coz(baslik.strip(), dosya)
            kaynak_id = f"{dosya}#kart-{no}"
            duzeltilmis = hitap_duzelt(govde)
            cikti, _, sorun = kart_coz(duzeltilmis)
            if cikti is None:
                raise ValueError(f"{kaynak_id}: kart çözülemedi: {sorun}")
            sorun = sorted(set(sorun + altin_sorunlari(cikti)))
            if not sorun and cikti in gorulen:
                sorun = ["mukerrer"]
            c = rapor[("altin", dosya, "kart")]
            c["toplam"] += 1
            if duzeltilmis != govde:
                c["duzeltme:hitap"] += 1
            if sorun:
                for x in sorun:
                    c["sorun:" + x] += 1
                sorunlu.append({"kaynak": dosya, "kaynak_id": kaynak_id, "tur": "kart", "sorunlar": sorun, "malzeme": malzeme, "prompt": None, "ham": govde})
                continue
            gorulen[cikti] = kaynak_id
            c["temiz"] += 1
            temiz.append(kayit(sayac, "altin", "kart", dosya, kaynak_id, malzeme, cikti))
    return temiz, sorunlu


def main():
    os.makedirs(TEMIZ, exist_ok=True)
    sayac = collections.Counter()
    rapor = collections.defaultdict(collections.Counter)
    model, model_s = model_isle(sayac, rapor)
    yaz("model_ciktilari.jsonl", model)
    silinenleri_yaz("model_silinenler.jsonl", model_s)
    altin, altin_s = altin_isle(sayac, rapor)
    yaz("altin_set.jsonl", altin)
    silinenleri_yaz("altin_silinenler.jsonl", altin_s)
    for (set_adi, dosya, tur), c in sorted(rapor.items()):
        print(f"{set_adi:6} {dosya:40} {tur:7} toplam={c['toplam']:5} temiz={c['temiz']:5}")
        for k, v in sorted(c.items()):
            if ":" in k:
                print(f"         {k}: {v}")
    print(f"\nMODEL temiz={len(model)} elenen={len(model_s)}")
    print(f"ALTIN temiz={len(altin)} elenen={len(altin_s)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
