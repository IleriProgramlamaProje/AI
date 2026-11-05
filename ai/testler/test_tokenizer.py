"""M5 tokenizer testleri (küçük veriyle eğitir, birkaç saniye).   cd AI && python -m pytest ai/testler/test_tokenizer.py"""
import pytest

pytest.importorskip("tokenizers")

from ai.ortak.kart_bicimi import egitim_metni, metinden_karta            # noqa: E402
from ai.testler.test_kart_bicimi import COBAN_KART, COBAN_MALZEME, ELLE  # noqa: E402
from ai.tokenizer.egit_tokenizer import SON, egit, kart_etiketleri      # noqa: E402

HIKAYE = ("Köyün kuyusu kurudu. Çiftçi Ali sabah erkenden kalktı, kazmasını aldı ve dağa yürüdü. "
          "Akşama kadar taşları kazdı, sonunda soğuk bir pınar buldu. Köylüler sevindi, kral da ona bir kese altın verdi.")


@pytest.fixture(scope="module")
def tok(tmp_path_factory):
    yol = tmp_path_factory.mktemp("tok") / "veri.txt"
    belgeler = [HIKAYE] * 20 + [egitim_metni(COBAN_KART, COBAN_MALZEME)] * 5 + [egitim_metni(k, m) for k, m in ELLE] * 5
    yol.write_text("\n\n".join(belgeler), encoding="utf-8")
    return egit([yol], boyut=600)


def test_kart_etiketleri_tek_token(tok):
    for e in kart_etiketleri() + [SON]:
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

