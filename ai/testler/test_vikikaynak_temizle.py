"""vikikaynak_temizle.py (S3): Vikikaynak artıkları silinir, eski dilli eser atılır.
cd AI && python -m pytest ai/testler/test_vikikaynak_temizle.py"""
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "ai" / "veri_hazirlama"))
import vikikaynak_temizle as v  # noqa: E402


def test_temizle_baslik_telif_kaynak_ve_notlar():
    ham = ("Zeytin Ekmek\n\nBu maddede yer alan eserin telif bilgisi belirsizdir.\n"
           "Maddeye eserin telif hakkı bilgisini girerek Vikikaynak'a katkıda bulunabilirsiniz.\n"
           "Genç kadın görmediğim(-me,isim fiil) sokağa baktı[1].\n\n🙝🙟\n\n"
           "Hoca bir tane yer,dayanamaz.\n. . . . .\nDipnotlar\n\nSayfa başı\nKaynakça")
    assert v.temizle(ham) == "Genç kadın görmediğim sokağa baktı.\nHoca bir tane yer, dayanamaz."


def test_kaynak_satirindan_sonrasi_kesilir():
    ham = "Başlık\nHoca güldü.\nKaynak : http://www.kalem.biz\nTelif durumu:\nBu maddede yer alan eser anonimdir"
    assert v.temizle(ham) == "Hoca güldü."


def test_bakim_notu_basta_ise_metin_kalir():
    ham = ("Nâdan\nBu çalışmanın düzen ve biçim olarak Vikikaynak standartlarına ulaşması için elden geçirilmesi gerekmektedir.\n"
           "Eğer yardım etmek isterseniz, yardım sayfasına bakabilirsiniz.\n\nNâdan ile sohbet etmek güçtür.")
    assert v.temizle(ham) == "Nâdan ile sohbet etmek güçtür."


def test_eski_dil():
    assert v.eski_mi("Dimişler Nâsırüddin Hâceye âh\nDüşüben oğlun ussı gitdi nâgâh")
    assert not v.eski_mi("Dımışk'a vardı. Sesini işitti, didik didik aradı. Dımışk büyüktü.")


def test_klasor_ciktisi(tmp_path):
    k = tmp_path / "Nasreddin Hoca fıkraları"
    k.mkdir()
    (k / "a.txt").write_text("A\n\nHoca eşeğe ters binmiş.\n\nHerkes gülmüş.", encoding="utf-8")
    (k / "b.txt").write_text("B\nDimiş ussı gitdi nâgâh", encoding="utf-8")
    belgeler, atilan = v.klasoru_isle(k)
    assert belgeler == ["Hoca eşeğe ters binmiş.\nHerkes gülmüş."] and atilan == ["b.txt"]
