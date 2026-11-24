#!/usr/bin/env python3
"""S3 · Edebiyat: Vikikaynak'tan indirilmiş .txt dosyalarını temizler, data/edebiyat/ altına yazar.

    python ai/veri_hazirlama/vikikaynak_temizle.py ~/Downloads/vikikaynak_hikayeler      # zip açılmış klasör

Girdi klasöründe yazar başına bir alt klasör, her eser bir .txt (ilk satır başlık). Okunan klasörler (KLASORLER):
  "Ömer Seyfettin hikayeleri" → data/edebiyat/omer_seyfettin.txt
  "Nasreddin Hoca fıkraları"  → data/edebiyat/nasreddin_hoca.txt
Dede Korkut alınmaz: tek boy var, noktalamasız ve eski yazımla (bkz. data/edebiyat/KAYNAK.md).

Temizlik:
  - Başlık satırı, Vikikaynak'ın telif uyarısı ("Bu maddede yer alan eserin telif bilgisi belirsizdir..." bloğu) silinir.
  - "Kaynak:", "Telif durumu:", "Dipnotlar", "Sayfa başı", "Kaynakça" ve Vikikaynak bakım/telif notlarından sonrası kesilir.
  - Süs ve nokta satırları ("🙝🙟", ". . . ."), dipnot işaretleri ([1]) ve dil bilgisi notları ("(-me,isim fiil)") silinir.
  - Paragraflar tek satır sonuyla birleşir (hazirla.py belgeleri boş satırla ayırır).
  - Eski dille (manzum, "dimiş", "oğlancuk"...) yazılmış eserler atılır.
"""
import argparse
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]

KLASORLER = {"Ömer Seyfettin hikayeleri": "omer_seyfettin.txt", "Nasreddin Hoca fıkraları": "nasreddin_hoca.txt"}
SON = re.compile(r"^(Kaynak\s*:|Telif durumu:|Dipnotlar$|Sayfa başı$|Kaynakça$|"
                 r"İlk kez Osmanlı İmparatorluğu'nda yayınlanan bu çalışma)")
TELIF_UYARISI = ("Bu maddede yer alan eserin telif bilgisi belirsizdir", "Vikikaynak'ta yalnızca telif hakkı serbest",
                 "Maddeye eserin telif hakkı bilgisini girerek",
                 "Bu çalışmanın düzen ve biçim olarak Vikikaynak", "Eğer yardım etmek isterseniz, yardım sayfasına")
SUS = re.compile(r"^[\s.·•*🙝🙟❧☙—–-]*$")
DIPNOT = re.compile(r"\[\d+\]|\(-[^)]*\)|\(-[^)]{0,30}?fiil")   # [1], dil bilgisi notu: görmediğim(-me,isim fiil)
# Küçük harfe çevrilmiş metinde aranır (re.I kullanılmaz: ı/i ayrımını bozar, "Dımışk" → "dimiş" olur).
ESKI = re.compile(r"\b(dimiş|oğlancuk|işüt|gitdi|ussı|nâgâh|idün|eyleyüp)\w*")


def temizle(metin):
    """Başlıksız, ek bilgisiz, belge içinde boş satır olmayan eser metni."""
    satirlar = metin.splitlines()[1:]          # ilk satır başlık
    temiz = []
    for s in satirlar:
        s = s.strip()
        if SON.match(s):
            break
        if not s or SUS.match(s) or s.startswith(TELIF_UYARISI):
            continue
        s = re.sub(r"\s+", " ", DIPNOT.sub("", s)).strip()
        s = re.sub(r",(?=[^\W\d])", ", ", s)    # "yer,dayanamaz" → "yer, dayanamaz"
        if s:
            temiz.append(s)
    return "\n".join(temiz)


def eski_mi(metin):
    return len(ESKI.findall(metin.replace("I", "ı").replace("İ", "i").lower())) >= 2


def klasoru_isle(klasor):
    """(belgeler, atılan dosya adları)."""
    belgeler, atilan = [], []
    for yol in sorted(klasor.glob("*.txt")):
        metin = temizle(yol.read_text(encoding="utf-8"))
        if not metin or eski_mi(metin):
            atilan.append(yol.name)
        else:
            belgeler.append(metin)
    return belgeler, atilan


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("girdi", help="Vikikaynak .txt'lerinin bulunduğu klasör (yazar başına alt klasör)")
    ap.add_argument("--cikti", default=str(KOK / "data" / "edebiyat"))
    args = ap.parse_args()
    girdi, cikti = Path(args.girdi).expanduser(), Path(args.cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    for ad, dosya in KLASORLER.items():
        if not (girdi / ad).is_dir():
            print(f"Uyarı: {girdi / ad} yok, atlandı.", file=sys.stderr)
            continue
        belgeler, atilan = klasoru_isle(girdi / ad)
        (cikti / dosya).write_text("\n\n".join(belgeler) + "\n", encoding="utf-8")
        kelime = sum(len(b.split()) for b in belgeler)
        print(f"{dosya}: {len(belgeler)} eser, {kelime:,} kelime; atılan: {atilan or '-'}")


if __name__ == "__main__":
    main()
