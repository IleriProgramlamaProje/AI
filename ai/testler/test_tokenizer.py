"""M5 tokenizer testleri (küçük veriyle eğitir, birkaç saniye).   cd AI && python -m pytest ai/testler/test_tokenizer.py"""
import pytest

pytest.importorskip("tokenizers")

from ai.ortak.kart_bicimi import egitim_metni, metinden_karta            # noqa: E402
from ai.testler.test_kart_bicimi import COBAN_KART, COBAN_MALZEME, ELLE  # noqa: E402
from ai.tokenizer.egit_tokenizer import SON, belgeler, egit, kart_etiketleri, yedek_etiketler  # noqa: E402

HIKAYE = ("Köyün kuyusu kurudu. Çiftçi Ali sabah erkenden kalktı, kazmasını aldı ve dağa yürüdü. "
          "Akşama kadar taşları kazdı, sonunda soğuk bir pınar buldu. Köylüler sevindi, kral da ona bir kese altın verdi.")


@pytest.fixture(scope="module")
def tok(tmp_path_factory):
    yol = tmp_path_factory.mktemp("tok") / "veri.txt"
    belgeler = [HIKAYE] * 20 + [egitim_metni(COBAN_KART, COBAN_MALZEME)] * 5 + [egitim_metni(k, m) for k, m in ELLE] * 5
    yol.write_text("\n\n".join(belgeler), encoding="utf-8")
    return egit([yol], boyut=600)


def test_kart_etiketleri_tek_token(tok):
    for e in kart_etiketleri() + yedek_etiketler() + [SON]:
        assert len(tok.encode(e).tokens) == 1, e


def test_cozulen_kart_okunur(tok):
    for kart, malzeme in [(COBAN_KART, COBAN_MALZEME), *ELLE]:
        metin = egitim_metni(kart, malzeme)
        geri = tok.decode(tok.encode(metin).ids, skip_special_tokens=False)
        assert metinden_karta(geri)[0] == kart


def test_hitap_bosluklari_korunur(tok):
    metin = "korkarım {hitap}. İçeri alalım mı?"
    assert tok.decode(tok.encode(metin).ids, skip_special_tokens=False) == metin


def test_kodla_bin_dosyasi_yazar(tok, tmp_path):
    np = pytest.importorskip("numpy")
    from ai.tokenizer.kodla import kodla
    yol = tmp_path / "t.json"
    tok.save(str(yol))
    bin_yol = tmp_path / "train.bin"
    adet = kodla(yol, [HIKAYE, HIKAYE], bin_yol)
    veri = np.fromfile(bin_yol, dtype=np.uint16)
    assert len(veri) == adet
    assert (veri == tok.token_to_id(SON)).sum() == 2
    assert tok.decode(veri[:adet // 2 - 1].tolist()) == HIKAYE



def test_istiyor_etiketli_kart_okunur(tok):
    metin = egitim_metni(COBAN_KART, COBAN_MALZEME, "Sağ")
    geri = tok.decode(tok.encode(metin).ids, skip_special_tokens=False)
    kart, malzeme = metinden_karta(geri)
    assert kart == COBAN_KART and malzeme["istedigi"] == "Sağ"


def test_yedek_etiketler_ayri_numarali(tok):
    numaralar = [tok.token_to_id(e) for e in yedek_etiketler()]
    assert None not in numaralar and len(set(numaralar)) == len(numaralar) == 20


@pytest.mark.parametrize("ham,duz", [("“Gel,” dedi.", '"Gel," dedi.'), ("«Gel» dedi.", '"Gel" dedi.'),
                                     ("Ali’nin atı", "Ali'nin atı"), ("Ali‘nin atı", "Ali'nin atı"),
                                     ("— Dur! – dedi.", "- Dur! - dedi.")])
def test_tirnak_kesme_tire_tek_bicim(tok, ham, duz):
    assert tok.encode(ham).ids == tok.encode(duz).ids


def test_temiz_kart_kaydi_dogrudan_okunur(tmp_path):
    import json
    yol = tmp_path / "temiz.jsonl"
    kayitlar = [{"tur": "hikaye", "cikti": HIKAYE},
                {"tur": "kart", "cikti": "Metin: ...", "kart": COBAN_KART, "malzeme": COBAN_MALZEME},
                {"tur": "kart", "cikti": "Metin: ham kart, kart alanı yok"}]
    yol.write_text("".join(json.dumps(k, ensure_ascii=False) + "\n" for k in kayitlar), encoding="utf-8")
    assert list(belgeler([yol])) == [HIKAYE, egitim_metni(COBAN_KART, COBAN_MALZEME)]
