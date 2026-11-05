"""Tokenizer nasıl bölüyor? (görev M5, incele.ipynb da bunu çağırır)

    python -m ai.tokenizer.incele                       # varsayılan ai/tokenizer/cikti/tokenizer.json
    python -m ai.tokenizer.incele --tokenizer yol/tokenizer.json
"""
import argparse

from tokenizers import Tokenizer

from ai.ortak.kart_bicimi import metinden_karta
from ai.tokenizer.egit_tokenizer import CIKTI, kart_etiketleri

# Gidiş-dönüş: kart metni token'lara bölünüp geri birleştirilince (decode) metinden_karta hâlâ okuyabiliyor mu?
ORNEK_KART = """<yonetim:10> <halk:15> <para:50> <ordu:25> <konu:kale_onarımı> <konuşan:coban>
<kart> Koyunları otlatırken kale kapısında kaba yabancı tüccarlar gördüm, {hitap}. İçeri alalım mı?
<sol> Tüccarları içeri al <yonetim-> <halk--> <para++>
<sonuc> Yabancılar pazara mal getirdi ama sürülere zarar verdi.
<sag> Tüccarları kapıdan koval <halk+> <para-->
<sonuc> Sürüler korundu ama tüccarlar komşu topraklara gitti.
</kart>"""

# 20 örnek: ekler üst üste binen kelimeler (ev → evlerimizden), ünlü uyumu, çağa özgü kelimeler, kart parçaları.
ORNEKLER = [
    "ev", "evler", "evlerimiz", "evlerimizden",
    "Kervanı sabah erkenden yola çıkardılar.",
    "Hazinedar altınları saydı ama hesap tutmadı.",
    "Akıncılar sınırın öte yanına geçmek istiyor.",
    "Köylüler ambarların açılmasını bekliyordu.",
    "Kadı iki tarafı dinlemeden hüküm vermez.",
    "Gözcü Başı gece yarısı surlarda bir ışık gördü.",
    "kervansaraylarımızdakilerden",
    "çiftçilerimizin tarlalarındaki buğdaylar",
    "Ozan meydanda türkü söyledi, halk alkışladı.",
    "Değirmenciler un fiyatını iki katına çıkardı.",
    "{hitap}, askerler üç aydır maaş alamadı.",
    "<sol> Ambarı aç <halk++> <para->",
    "<yonetim:50> <halk:40> <para:25> <ordu:60> <konu:kale_onarımı> <konuşan:akinci_beyi>",
    "<sonuc> Askerler sevindi, ama hazine iyice eridi.",
    "</kart>",
    "İstanbul'dan gelen elçi Şehzade'ye mektup getirdi.",
]


def bolunus(tok, metin):
    return tok.encode(metin).tokens


def etiket_kontrol(tok):
    """Her kart etiketi tek token mı? Tek olmayanların listesini döndürür (boş liste = hepsi tamam)."""
    return [e for e in kart_etiketleri() if len(tok.encode(e).tokens) != 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer", default=str(CIKTI))
    tok = Tokenizer.from_file(ap.parse_args().tokenizer)
    print(f"kelime dağarcığı: {tok.get_vocab_size()}\n")
    for m in ORNEKLER:
        t = bolunus(tok, m)
        print(f"{len(t):3d} token · {m}\n          {' | '.join(t)}")
    bozuk = etiket_kontrol(tok)
    geri = tok.decode(tok.encode(ORNEK_KART).ids, skip_special_tokens=False)
    print(f"\nörnek kart: {len(tok.encode(ORNEK_KART).ids)} token · çözülmüş hâli:\n{geri}")
    print("metinden_karta okuyabiliyor:", "evet ✓" if metinden_karta(geri)[0] == metinden_karta(ORNEK_KART)[0] else "HAYIR ✗")
    print("\nkart etiketleri:", "hepsi tek token ✓" if not bozuk else f"{len(bozuk)} tanesi bölünüyor: {bozuk[:10]}")


if __name__ == "__main__":
    main()
