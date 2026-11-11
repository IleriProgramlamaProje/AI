"""S2 kart_bicimi testleri.   cd AI && python -m pytest ai/testler/test_kart_bicimi.py -v"""
import json
import re

import pytest

from ai.ortak.ayarlar import ETKI_KADEMELERI, KOK
from ai.ortak.kart_bicimi import (KartBicimHatasi, egitim_metni, konu_ascii, metinden_karta, oyun_json)

# Altın setten gerçek bir kart (altin-0000007). Öğretmen etkileri Para, Halk, Yönetim sırasıyla yazmıştı.
COBAN_KART = {
    "metin": "Koyunları otlatırken kale kapısında kaba yabancı tüccarlar gördüm. Gece meşale yakıp içeri girmek isterler. Pınarlarımızı, otlaklarımızı kurutacaklar diye korkarım {hitap}. İçeri alalım mı, kovalım mı?",
    "sol": {"karar": "Tüccarları içeri al", "sonuc": "Yabancılar pazara mal getirdi ama koyun sürülerine zarar verdiler.", "etki": {"para": 10, "halk": -10, "yonetim": -5}},
    "sag": {"karar": "Tüccarları kapıdan koval", "sonuc": "Sürüler ve otlaklar korundu ama tüccarlar kızıp komşu topraklara gitti.", "etki": {"halk": 5, "para": -10}},
}
COBAN_MALZEME = {"karakter": "Çoban", "durum": {"Yönetim": 10, "Halk": 15, "Para": 50, "Ordu": 25}, "ekstra": {"konu": "serbest"}}
COBAN_METIN = """<yonetim:10> <halk:15> <para:50> <ordu:25> <konu:serbest> <konuşan:coban>
<kart> Koyunları otlatırken kale kapısında kaba yabancı tüccarlar gördüm. Gece meşale yakıp içeri girmek isterler. Pınarlarımızı, otlaklarımızı kurutacaklar diye korkarım {hitap}. İçeri alalım mı, kovalım mı?
<sol> Tüccarları içeri al <yonetim-> <halk--> <para++>
<sonuc> Yabancılar pazara mal getirdi ama koyun sürülerine zarar verdiler.
<sag> Tüccarları kapıdan koval <halk+> <para-->
<sonuc> Sürüler ve otlaklar korundu ama tüccarlar kızıp komşu topraklara gitti.
</kart>"""

# Farklı durumları kapsayan elle yazılmış kartlar: boşluklu konu, tek / üç etki, +++ / ---, çok kelimeli unvan.
ELLE = [
    ({"metin": "{hitap}, surun doğu duvarı yağmurda çöktü. Taş ustaları hazır ama ücret istiyorlar.",
      "sol": {"karar": "Ustalara altın öde", "sonuc": "Duvar bir haftada yükseldi, hazine azaldı.", "etki": {"para": -10, "ordu": 10}},
      "sag": {"karar": "Köylüleri angaryaya çağır", "sonuc": "Duvar yapıldı ama köylerde öfke büyüdü.", "etki": {"halk": -15}}},
     {"karakter": "Kale Kumandanı", "durum": {"Yönetim": 50, "Halk": 40, "Para": 60, "Ordu": 35}, "ekstra": {"konu": "kale onarımı"}}),
    ({"metin": "Sınırın öte yanından zengin mal yüklü bir kervan geçiyor. Akıncılarım izninizi bekliyor.",
      "sol": {"karar": "Akına izin ver", "sonuc": "Akıncılar ganimetle döndü, komşu elçisini geri çağırdı.", "etki": {"ordu": 15, "para": 5, "yonetim": -10}},
      "sag": {"karar": "Andı bozma", "sonuc": "Barış korundu, akıncılar söylendi.", "etki": {"ordu": -5}}},
     {"karakter": "Akıncı Beyi", "durum": {"Yönetim": 5, "Halk": 100, "Para": 0, "Ordu": 95}, "ekstra": {}}),
]


# ---------- egitim_metni ----------

def test_coban_karti_beklenen_metni_verir():
    assert egitim_metni(COBAN_KART, COBAN_MALZEME) == COBAN_METIN


def test_etkiler_hep_ayni_sirada():
    satirlar = egitim_metni(*ELLE[1]).splitlines()
    assert satirlar[2].endswith("<yonetim--> <para+> <ordu+++>")


def test_bosluklu_konu_alt_cizgi_olur_turkce_harf_kalir():
    assert "<konu:kale_onarımı>" in egitim_metni(*ELLE[0])


def test_konu_yoksa_serbest():
    assert "<konu:serbest>" in egitim_metni(*ELLE[1])


def test_bilinmeyen_karakter_hata():
    with pytest.raises(KeyError):
        egitim_metni(COBAN_KART, {**COBAN_MALZEME, "karakter": "Muhafız"})


def test_gecersiz_etki_degeri_hata():
    kart = json.loads(json.dumps(COBAN_KART))
    kart["sol"]["etki"]["para"] = 7
    with pytest.raises(ValueError):
        egitim_metni(kart, COBAN_MALZEME)


# ---------- gidiş-dönüş ----------

@pytest.mark.parametrize("kart,malzeme", [(COBAN_KART, COBAN_MALZEME), *ELLE])
def test_kart_metin_kart_ayni_karti_verir(kart, malzeme):
    k2, m2 = metinden_karta(egitim_metni(kart, malzeme))
    assert k2 == kart
    assert m2["karakter"] == malzeme["karakter"]
    assert m2["durum"] == malzeme["durum"]
    assert m2["ekstra"]["konu"] == (malzeme["ekstra"].get("konu") or "serbest")


def test_kart_sonrasi_fazlalik_atilir():
    k, _ = metinden_karta(COBAN_METIN + "\n<yonetim:50> <halk:50> ... <kart> yarım kalan ikinci kart")
    assert k == COBAN_KART


# ---------- oyun_json ----------

def test_json_alanlari_kart_formati_3_bolum():
    j = oyun_json(COBAN_KART, COBAN_MALZEME)
    assert set(j) == {"konusan", "konu", "metin", "sol", "sag", "kaynak", "lisans"}
    assert set(j["sol"]) == set(j["sag"]) == {"etiket", "etki", "sonuc"}
    assert j["konusan"] == "coban" and j["kaynak"] == "ogretmen" and j["lisans"] == "sadece_ders"
    assert j["sol"]["etiket"] == "Tüccarları içeri al"
    assert j["sol"]["etki"] == {"yonetim": -5, "halk": -10, "para": 10}


def test_json_konu_ascii():
    assert oyun_json(*ELLE[0])["konu"] == "kale_onarimi"
    assert konu_ascii("İhanet ve Şüphe") == "ihanet_ve_suphe"


def test_json_kaynak_kontrol():
    assert oyun_json(*ELLE[0], kaynak="altin_set")["kaynak"] == "altin_set"
    with pytest.raises(ValueError):
        oyun_json(*ELLE[0], kaynak="baska")


# ---------- metinden_karta: bozuk metinler hata vermeli ----------

def _bozuk(eski, yeni):
    assert eski in COBAN_METIN
    return COBAN_METIN.replace(eski, yeni, 1)


BOZUK = {
    "sag_yok": "\n".join(COBAN_METIN.splitlines()[:4]) + "\n</kart>",
    "kart_kapanmamis": COBAN_METIN.replace("\n</kart>", ""),
    "bilinmeyen_gosterge": _bozuk("<halk+>", "<asker+>"),
    "dort_arti": _bozuk("<halk+>", "<halk++++>"),
    "sayili_etki": _bozuk("<halk+>", "<halk+10>"),
    "etkisiz_secenek": _bozuk(" <halk+> <para-->", ""),
    "ayni_gosterge_iki_kez": _bozuk("<halk+> <para-->", "<halk+> <halk-->"),
    "dort_gosterge": _bozuk("<halk+> <para-->", "<yonetim+> <halk+> <para--> <ordu->"),
    "bilinmeyen_konusan": _bozuk("<konuşan:coban>", "<konuşan:muhafiz>"),
    "durum_sayi_degil": _bozuk("<para:50>", "<para:abc>"),
    "durum_eksik": _bozuk(" <ordu:25>", ""),
    "durum_100_ustu": _bozuk("<para:50>", "<para:150>"),
    "konu_yok": _bozuk(" <konu:serbest>", ""),
    "karar_bos": _bozuk("<sol> Tüccarları içeri al <", "<sol> <"),
    "sonuc_bos": _bozuk("<sonuc> Yabancılar pazara mal getirdi ama koyun sürülerine zarar verdiler.", "<sonuc>"),
    "kart_metni_bos": re.sub(r"<kart> .*\n", "<kart>\n", COBAN_METIN, count=1),
    "etiketler_arasinda_yazi": _bozuk("<halk+> <para-->", "<halk+> ve <para-->"),
    "tek_satir": COBAN_METIN.splitlines()[0],
}


@pytest.mark.parametrize("ad", BOZUK)
def test_bozuk_metin_hata_verir(ad):
    with pytest.raises(KartBicimHatasi):
        metinden_karta(BOZUK[ad])


SATIRLI = """Metin: Koyunlar aç kaldı {hitap}.
Sol: Otlağı aç
Sol sonuç: Sürü doydu.
Sol etki: Halk ++, Para -
Sağ: Otlağı kapalı tut
Sağ sonuç: Sürü zayıfladı.
Sağ etki: Halk ---"""


def test_satirli_karta():
    from ai.ortak.kart_bicimi import satirli_karta
    k = satirli_karta(SATIRLI)
    assert k["metin"] == "Koyunlar aç kaldı {hitap}."
    assert k["sol"] == {"karar": "Otlağı aç", "sonuc": "Sürü doydu.", "etki": {"halk": 10, "para": -5}}
    assert k["sag"]["etki"] == {"halk": -15}


@pytest.mark.parametrize("bozuk", [SATIRLI.replace("Sağ etki: Halk ---", ""), SATIRLI.replace("Halk ---", "Halk +10"),
                                   SATIRLI.replace("Halk ---", "Hazine -"), SATIRLI.replace("Halk ---", "Halk -, Halk -")])
def test_satirli_karta_bozuk(bozuk):
    from ai.ortak.kart_bicimi import KartBicimHatasi, satirli_karta
    with pytest.raises(KartBicimHatasi):
        satirli_karta(bozuk)

