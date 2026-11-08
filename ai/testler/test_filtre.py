"""filtre.py (S1): doğru metin geçer, bozuk metin sebebiyle elenir.   cd AI && python -m pytest ai/testler/test_filtre.py"""
import json
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(KOK), str(KOK / "ai" / "filtre")]
import filtre  # noqa: E402

BETIK = KOK / "ai" / "filtre" / "filtre.py"
METIN = ("Koyunlarım otlakta aç kaldı {hitap}, kuyular kurudu ve çobanlar köye dönmek istiyor. "
         "Bu kış sürü dağılırsa pazarda yün de et de bulunmaz.")
HIKAYE = ("Kervan sabah erkenden yola çıktı. " * 6 + "Yaşlı çoban yorgun gözlerle ufka baktı ve yavaşça kalktı. " * 6
          + "Kuyunun başında herkes bekliyordu, çünkü su azalmıştı ve köy susuz kalmıştı. " * 3).strip()


def _kart(metin=METIN, sol="Yeni otlak aç"):
    return (f"Metin: {metin}\nSol: {sol}\nSol sonuç: Sürü doydu ama hazineden para gitti.\nSol etki: Halk ++, Para -\n"
            "Sağ: Çobanları bekle\nSağ sonuç: Hazine korundu ama sürü zayıfladı.\nSağ etki: Para +, Halk --")


def _kayit(no, cikti, tur="kart", kelimeler=("otlak", "aç"), karakter="Çoban"):
    return {"surum": 3, "id": f"{tur}-{no:07d}", "tur": tur, "prompt": f"prompt {no}", "cikti": cikti,
            "malzeme": {"tur": tur, "karakter": karakter, "kelimeler": list(kelimeler), "ekstra": {},
                        "durum": {"Yönetim": 50, "Halk": 40, "Para": 25, "Ordu": 60} if tur == "kart" else {}},
            "model": "deneme", "motor": "sahte", "tohum": "t", "token": 1, "saniye": 0.1}


def _sorun(kayit, **kw):
    return filtre.kayit_sorunlari(kayit, **kw)[2]


def test_bozuk_kelime_yakalanir():
    for kelime in ("taşleri", "halkınin", "insanler", "çocuklerin", "atınin", "evlar"):
        assert filtre.bozuk_mu(kelime), kelime


def test_dogru_ve_alinti_kelimeler_gecer():
    for kelime in ("taşları", "halkının", "evleri", "saatler", "harpler", "valinin", "gazinin", "kalpleri",
                   "hallerine", "cemaatler", "metalleri", "kontrolleri", "karantina", "anne", "elma", "kervanları", "meydan", "kadının"):
        assert not filtre.bozuk_mu(kelime), kelime


def test_yakalanamayan_hata_kabul_edilir():
    # "arkadaşinin" yazılışı doğru bir kelimeyle aynı (arkadaşi-nin değil arkadaş-ı-nın): yz_gorevleri.md'de kabul edildi
    assert not filtre.bozuk_mu("arkadaşinin")


def test_modern_kelime_tam_kelime_olarak_aranir():
    assert filtre.modern_kelimeler("Bakan geldi") == ["bakan"]
    assert filtre.modern_kelimeler("Politikası değişti") == ["politikası"]
    assert filtre.modern_kelimeler("Depolarda buğday var, ufka bakanlar sustu") == []


def test_iyi_kart_gecer_ve_ayrisir():
    cikti, kart, sorun, _ = filtre.kayit_sorunlari(_kayit(1, _kart()))
    assert sorun == []
    assert kart["sol"] == {"karar": "Yeni otlak aç", "sonuc": "Sürü doydu ama hazineden para gitti.",
                           "etki": {"halk": 10, "para": -5}}
    assert kart["sag"]["etki"] == {"para": 5, "halk": -10}


def test_kart_kurallari():
    assert _sorun(_kayit(1, "[BOŞ ÇIKTI]")) == ["bos_cikti"]
    assert "bozuk_kelime" in _sorun(_kayit(1, _kart(METIN.replace("çobanlar", "çobanler"))))
    assert "modern_kelime" in _sorun(_kayit(1, _kart(METIN.replace("çobanlar", "memurlar") + " Bakan da kızgın.")))
    assert _sorun(_kayit(1, _kart(), kelimeler=("hisar", "kısa"))) == ["kelime_gecmiyor"]
    assert _sorun(_kayit(1, _kart(), kelimeler=("hisar", "aç"))) == []          # kartta ikisinden biri yeter
    assert _sorun(_kayit(1, _kart(), kelimeler=("hisar", "kısa")), kelime_kontrolu=False) == []
    assert "yasak_hitap" in _sorun(_kayit(1, _kart(METIN.replace("{hitap}", "Beyim"))))
    assert "karar>5" in _sorun(_kayit(1, _kart(sol="Yeni ve geniş bir otlak hemen aç")))
    # Model satır başına ** ya da - koyabilir: tolere edilir
    assert _sorun(_kayit(1, "\n".join("- " + s for s in _kart().split("\n")))) == []


def test_hikaye_kurallari():
    kelimeler = ("kervan", "kalkmak", "yorgun")
    assert _sorun(_kayit(1, HIKAYE, "hikaye", kelimeler)) == []
    assert _sorun(_kayit(1, "Başlık: Kervan\n" + HIKAYE, "hikaye", kelimeler)) == []    # başlık satırı silinir
    assert _sorun(_kayit(1, HIKAYE, "hikaye", ("kervan", "kalkmak", "mutsuz"))) == ["kelime_gecmiyor"]  # üçü de gerekli
    assert "hikaye<90" in _sorun(_kayit(1, "Kervan yola çıktı, yorgun çoban kalktı.", "hikaye", kelimeler))


def test_filtre_uctan_uca(tmp_path):
    (tmp_path / "ham").mkdir()
    kayitlar = [_kayit(1, _kart()), _kayit(2, _kart()), _kayit(3, "[BOŞ ÇIKTI]"),
                _kayit(4, _kart(METIN.replace("çobanlar", "çobanler")))]
    (tmp_path / "ham" / "kart_t.jsonl").write_text("".join(json.dumps(k, ensure_ascii=False) + "\n" for k in kayitlar),
                                                   encoding="utf-8")
    subprocess.run([sys.executable, str(BETIK), str(tmp_path)], check=True, capture_output=True)
    cikti = tmp_path / "filtre"
    temiz = [json.loads(s) for s in (cikti / "temiz" / "kart_t.jsonl").read_text(encoding="utf-8").splitlines()]
    elenen = [json.loads(s) for s in (cikti / "elenen" / "kart_t.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [k["id"] for k in temiz] == ["kart-0000001"]
    assert temiz[0]["kart"]["metin"] == METIN
    assert {e["kaynak_id"].split("#")[1]: e["sebep_kodu"] for e in elenen} == {
        "kart-0000002": ["mukerrer"], "kart-0000003": ["bos_cikti"], "kart-0000004": ["bozuk_kelime"]}
    assert elenen[2]["bozuk"] == ["çobanler"]
    rapor = json.loads((cikti / "rapor.json").read_text(encoding="utf-8"))
    assert rapor["sebep"] == {"mukerrer": 1, "bos_cikti": 1, "bozuk_kelime": 1}
    assert "bozuk_kelime" in (cikti / "rapor.md").read_text(encoding="utf-8")
