#!/usr/bin/env python3
"""S3 · BİLGEM hikâyeleri: BILGE-Synthetic-Stories'ten temiz bir parça indirir, data/edebiyat/bilgem/bilgem.txt yazar.

    python ai/veri_hazirlama/bilgem_indir.py                       # varsayılan: ~1,5 milyon kelime
    python ai/veri_hazirlama/bilgem_indir.py --hedef 800000 --mb 80
    python ai/veri_hazirlama/bilgem_indir.py --girdi yerel.jsonl   # indirmeden, elde olan dosyadan

Kaynak: https://huggingface.co/datasets/BILGEM-AI/BILGE-Synthetic-Stories (Apache 2.0, 43 dosya, 16,8 GB).
Hepsi gerekmez: tek dosyanın ilk --mb megabaytı akış hâlinde okunur, gerisi indirilmez.

Ayıklananlar (sebep sayıları ekrana ve KAYNAK.md'ye yazılır):
  ingilizce : başta İngilizce model girişi ("Okay, here's a story...") ya da metinde İngilizce kelime / q-w-x'li kelime
  forum     : Reddit / forum anlatısı
  modern    : tema.json yasak kelimeleri + MODERN_EK (oyunun dünyasına uymayan modern kelimeler), yıl (19xx/20xx)
  kisa      : temizlikten sonra KISA_SINIR kelimeden az
  tekrar    : aynı metin ikinci kez
Temizlik: hikâyeden sonra gelen İngilizce not kesilir, "#" başlık satırları ve "---" çizgileri silinir, ** / __ / madde işaretleri kalkar. Paragraflar tek satır
sonuyla birleşir (hazirla.py belgeleri boş satırla ayırır, belge içinde boş satır olmamalı).
Masal / çocuk hikâyesi tarzındakiler öne alınır, hedefe yetmezse diğerleriyle tamamlanır.
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from ai.ortak.ayarlar import TEMA_DOSYASI  # noqa: E402

DEPO = "BILGEM-AI/BILGE-Synthetic-Stories"
URL = f"https://huggingface.co/datasets/{DEPO}/resolve/main/train-{{:05d}}-of-00043_generated.json"
LISANS = "Apache 2.0"
KISA_SINIR = 150

YASAK = tuple(json.loads(Path(TEMA_DOSYASI).read_text(encoding="utf-8"))["yasak_kelimeler"])
# Örnek veride görülen ve oyunun dünyasına (eski Türk / Osmanlı) uymayan kelimeler; ek almış halleri de yakalanır.
MODERN_EK = (
    "apartman", "asansör", "bilgisayar", "bisiklet", "benzin", "banka", "bilet", "dijital", "diyet", "doktor",
    "egzersiz", "ekran", "elektrik", "fabrika", "fotoğraf", "futbol", "gazete", "internet", "kamera", "kredi",
    "laboratuvar", "maaş", "makine", "market", "medya", "mesaj", "metro", "motor", "mühendis", "ofis", "otel",
    "otobüs", "otopark", "patron", "pizza", "plastik", "polis", "psikolog", "radyo", "restoran", "robot", "sinema",
    "sosyal", "spor", "staj", "stres", "şirket", "taksi", "teknoloji", "televizyon", "terapi", "tren", "uçak",
    "uygulama", "üniversite", "video", "virüs", "vitamin", "yazılım", "yoga",
)
INGILIZCE = {"the", "and", "you", "with", "this", "that", "of", "for", "here", "story", "okay", "is", "are", "my"}
FORUM = re.compile(r"reddit|\br/\w+|forum", re.I)
YIL = re.compile(r"\b(19|20)\d\d\b")
MASAL = re.compile(r"\b(minik|bir zamanlar|evvel zaman|masal|tavşan|tilki|kaplumbağa|ayıcık|sincap|orman|"
                   r"köy|nine|dede|büyükanne|büyükbaba|çocuk)", re.I)


def _kucuk(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def kelimeler(metin):
    return re.findall(r"[a-zçğıöşüâîû]+", _kucuk(metin))


def modern_mu(k):
    if any(k == y or (len(y) >= 6 and k.startswith(y)) for y in YASAK):
        return True
    return any(k.startswith(y) for y in MODERN_EK)


NOT_BASLIGI = {"explanation", "translation", "notes", "note", "breakdown", "context", "integration", "science"}


def ingilizce_satir(s):
    """3+ İngilizce kelime, ya da Türkçe harf içermeyen ve 2+ İngilizce kelimeli satır ("Translation Notes:")."""
    ks = re.findall(r"[a-z']+", s.lower())
    if sum(k in INGILIZCE for k in ks) >= 3:
        return True
    return not re.search(r"[çğıöşüÇĞİÖŞÜ]", s) and sum(k in INGILIZCE or k in NOT_BASLIGI for k in ks) >= 2


def temizle(metin):
    """Markdown işaretlerini atar, paragrafları tek satır sonuyla birleştirir. Hikâyeden sonra gelen İngilizce
    not ("Here's an explanation of the twist...") ve sonrası kesilir."""
    satirlar = []
    for s in metin.splitlines():
        s = s.strip()
        if satirlar and ingilizce_satir(s):
            break
        if not s or s.startswith("#") or re.fullmatch(r"[-*_=]{3,}", s):
            continue
        s = re.sub(r"\*\*|__|(?<!\w)\*|\*(?!\w)", "", s)
        s = re.sub(r"^[*\-•]\s+", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        if s:
            satirlar.append(s)
    return "\n".join(satirlar)


def eleme_sebebi(ham, temiz):
    """Kayıt atılacaksa sebebi, kalacaksa None."""
    if ingilizce_satir(ham[:300]):
        return "ingilizce"
    if FORUM.search(ham):
        return "forum"
    ks = kelimeler(temiz)
    if any(k in INGILIZCE or re.search(r"[qwx]", k) for k in ks):
        return "ingilizce"
    if YIL.search(temiz) or any(modern_mu(k) for k in ks):
        return "modern"
    if len(temiz.split()) < KISA_SINIR:
        return "kisa"
    return None


def masal_mi(temiz):
    return bool(MASAL.search(temiz[:500]))


def satirlar(girdi, dosya_no, mb):
    """jsonl satırları: yerel dosyadan ya da Hugging Face'ten akışla, ilk `mb` megabayt."""
    sinir, okunan = mb * 1024 * 1024, 0
    kaynak = open(girdi, "rb") if girdi else urllib.request.urlopen(URL.format(dosya_no), timeout=60)
    with kaynak as f:
        for satir in f:
            okunan += len(satir)
            if okunan > sinir:
                break
            yield satir.decode("utf-8", errors="ignore")


def topla(satir_akisi, hedef):
    """(seçilenler, sayımlar). Önce masal tarzı, sonra diğerleri; toplam kelime hedefe ulaşınca durur."""
    sayim = {"okunan": 0, "ingilizce": 0, "forum": 0, "modern": 0, "kisa": 0, "tekrar": 0}
    masal, diger, gorulen = [], [], set()
    for satir in satir_akisi:
        try:
            ham = json.loads(satir)["text"]
        except (ValueError, KeyError, TypeError):
            continue
        sayim["okunan"] += 1
        temiz = temizle(ham)
        sebep = eleme_sebebi(ham, temiz)
        if sebep is None:
            h = hashlib.md5(temiz.encode()).hexdigest()
            if h in gorulen:
                sebep = "tekrar"
            gorulen.add(h)
        if sebep:
            sayim[sebep] += 1
            continue
        (masal if masal_mi(temiz) else diger).append(temiz)
    secilen, kelime = [], 0
    for t in masal + diger:
        if kelime >= hedef:
            break
        secilen.append(t)
        kelime += len(t.split())
    sayim.update(uygun=len(masal) + len(diger), uygun_masal=len(masal), secilen=len(secilen),
                 secilen_masal=min(len(masal), len(secilen)), kelime=kelime)
    return secilen, sayim


def kaynak_notu(sayim, args):
    sebepler = "\n".join(f"| {k} | {sayim[k]:,} |" for k in ("ingilizce", "forum", "modern", "kisa", "tekrar"))
    return f"""# bilgem/

`bilgem.txt`: [{DEPO}](https://huggingface.co/datasets/{DEPO}) veri setinden temizlenmiş parça. Lisans: **{LISANS}**.
27B parametreli bir modelle Cosmopedia yöntemiyle üretilmiş sentetik Türkçe hikâyeler.

Üreten: `python ai/veri_hazirlama/bilgem_indir.py --dosya {args.dosya} --mb {args.mb} --hedef {args.hedef}`
(kaynak dosya: `train-{args.dosya:05d}-of-00043_generated.json`, ilk {args.mb} MB).

| | Sayı |
| --- | --- |
| Okunan kayıt | {sayim['okunan']:,} |
| Uygun (temizlikten geçen) | {sayim['uygun']:,} (masal tarzı {sayim['uygun_masal']:,}) |
| Dosyaya yazılan | {sayim['secilen']:,} (masal tarzı {sayim['secilen_masal']:,}) |
| Kelime | {sayim['kelime']:,} |

Elenenler:

| Sebep | Kayıt |
| --- | --- |
{sebepler}

Kurallar betiğin başındaki açıklamada. Belgeler arasında boş satır var.
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dosya", type=int, default=6, help="kaynak dosya numarası (6-42)")
    ap.add_argument("--mb", type=int, default=150, help="kaynak dosyanın ilk kaç MB'ı okunsun")
    ap.add_argument("--hedef", type=int, default=1_500_000, help="hedef kelime sayısı")
    ap.add_argument("--girdi", help="indirmek yerine yerel jsonl")
    ap.add_argument("--cikti", default=str(KOK / "data" / "edebiyat" / "bilgem"))
    args = ap.parse_args()

    secilen, sayim = topla(satirlar(args.girdi, args.dosya, args.mb), args.hedef)
    cikti = Path(args.cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    (cikti / "bilgem.txt").write_text("\n\n".join(secilen) + "\n", encoding="utf-8")
    (cikti / "KAYNAK.md").write_text(kaynak_notu(sayim, args), encoding="utf-8")
    print(json.dumps(sayim, ensure_ascii=False, indent=1))
    if sayim["kelime"] < args.hedef:
        print(f"Uyarı: hedefin altında kaldı ({sayim['kelime']:,} < {args.hedef:,}); --mb artırın.", file=sys.stderr)


if __name__ == "__main__":
    main()
