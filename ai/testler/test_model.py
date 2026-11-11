"""Model, eğitim ve örnekleme testleri (CPU, birkaç saniye).   cd AI && python -m pytest ai/testler/test_model.py"""
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
np = pytest.importorskip("numpy")
yaml = pytest.importorskip("yaml")

from ai.model.model import GPT, Ayar  # noqa: E402

KOK = Path(__file__).resolve().parents[2]
BOYUTLAR = KOK / "ai" / "model" / "boyutlar"
KUCUK = Ayar(sozluk=300, baglam=32, katman=2, kafa=2, genislik=32)


def test_cikti_boyutlari_ve_kayip():
    m = GPT(KUCUK)
    x = torch.randint(0, 300, (3, 32))
    logits, kayip = m(x, x)
    assert logits.shape == (3, 32, 300)
    # rastgele başlangıçta kayıp ~ ln(sözlük): her token eşit olası
    assert abs(kayip.item() - np.log(300)) < 0.5
    logits, kayip = m(x)
    assert logits.shape == (3, 1, 300) and kayip is None


def test_nedensellik_gelecek_gecmisi_etkilemez():
    m = GPT(KUCUK).eval()
    x = torch.randint(0, 300, (1, 20))
    y = x.clone()
    y[0, 15:] = (y[0, 15:] + 1) % 300
    with torch.no_grad():
        a = m.cikis(m.ln_son(_gizli(m, x)))[0, :15]
        b = m.cikis(m.ln_son(_gizli(m, y)))[0, :15]
    assert torch.allclose(a, b, atol=1e-5)


def _gizli(m, idx):
    x = m.tok_gom(idx) + m.konum_gom(torch.arange(idx.shape[1]))
    for blok in m.bloklar:
        x = blok(x)
    return x


def test_agirlik_paylasimi():
    m = GPT(KUCUK)
    assert m.cikis.weight is m.tok_gom.weight


@pytest.mark.parametrize("ad,hedef", [("1m", 1.2e6), ("10m", 10e6), ("30m", 30e6)])
def test_boyut_dosyalari_adina_uygun(ad, hedef):
    ayar = Ayar.sozlukten(yaml.safe_load(open(BOYUTLAR / f"{ad}.yaml", encoding="utf-8")))
    n = GPT(ayar).parametre_sayisi()
    assert 0.8 * hedef < n < 1.2 * hedef, f"{ad}: {n / 1e6:.2f}M"


def test_uret_durma_tokeninde_durur():
    torch.manual_seed(0)
    m = GPT(KUCUK)
    x = torch.zeros((1, 1), dtype=torch.long)
    cikti = m.uret(x, 50, top_k=1)            # top_k=1: hep en olası token, sonuç belirli
    dur = cikti[0, 1].item()                  # ilk üretilen token'ı durma token'ı yap
    kisa = m.uret(x, 50, top_k=1, dur=dur)
    assert kisa.shape[1] == 2
    uzun = m.uret(torch.zeros((1, 40), dtype=torch.long), 5)  # bağlamdan uzun girdi kırpılır, hata vermez
    assert uzun.shape[1] == 45


def test_egit_kucuk_veride_kayip_duser(tmp_path):
    """Tekrar eden bir dizi: model ezberleyebilmeli, val kaybı belirgin düşmeli. Kayıt noktası ve csv yazılmalı."""
    import sys
    sys.path.insert(0, str(KOK / "ai" / "egitim"))
    import egit
    desen = np.tile(np.arange(50, dtype=np.uint16), 400)
    (tmp_path / "veri").mkdir()
    desen.tofile(tmp_path / "veri" / "train.bin")
    desen[:3000].tofile(tmp_path / "veri" / "val.bin")
    boyut = tmp_path / "kucuk.yaml"
    boyut.write_text("sozluk: 64\nbaglam: 32\nkatman: 2\nkafa: 2\ngenislik: 32\nyigin: 16\nogrenme_orani: 0.01\ntur: 1\n")
    cikti = tmp_path / "model"
    en_iyi = egit.main(["--boyut", str(boyut), "--veri", str(tmp_path / "veri"), "--cikti", str(cikti),
                        "--adim", "150", "--olcum-araligi", "50", "--olcum-tekrar", "3", "--cihaz", "cpu"])
    assert en_iyi < 1.0                        # başlangıç ~ln(64)=4,2
    assert (cikti / "en_iyi.pt").exists() and (cikti / "son.pt").exists()
    satirlar = (cikti / "kayip.csv").read_text().strip().splitlines()
    assert satirlar[0].startswith("adim,train,val") and len(satirlar) == 5   # 0, 50, 100, 149

    # devam: son.pt'den sürer, csv silinmez
    egit.main(["--boyut", str(boyut), "--veri", str(tmp_path / "veri"), "--cikti", str(cikti),
               "--adim", "200", "--olcum-araligi", "50", "--olcum-tekrar", "3", "--cihaz", "cpu", "--devam"])
    assert len((cikti / "kayip.csv").read_text().strip().splitlines()) > 5

    # sözlükten büyük token varsa anlaşılır hata
    np.array([0, 1, 99] * 200, dtype=np.uint16).tofile(tmp_path / "veri" / "val.bin")
    with pytest.raises(SystemExit, match="sözlük"):
        egit.main(["--boyut", str(boyut), "--veri", str(tmp_path / "veri"), "--cikti", str(tmp_path / "m2"), "--cihaz", "cpu"])


def test_ornek_uret_kart_modu(tmp_path):
    """Eğitilmemiş modelle bile uçtan uca çalışır; kartlar bozuk çıkar ama rapor ve jsonl yazılır."""
    pytest.importorskip("tokenizers")
    import json
    import sys
    sys.path.insert(0, str(KOK / "ai" / "ornekleme"))
    import ornek_uret
    from ai.testler.test_tokenizer import HIKAYE
    from ai.tokenizer.egit_tokenizer import egit as tok_egit
    yol = tmp_path / "veri.txt"
    yol.write_text("\n\n".join([HIKAYE] * 20), encoding="utf-8")
    tok = tok_egit([yol], boyut=400)
    tok.save(str(tmp_path / "tok.json"))
    m = GPT(Ayar(sozluk=tok.get_vocab_size(), baglam=64, katman=1, kafa=2, genislik=16))
    torch.save({"model": m.state_dict(), "ayar": vars(m.ayar)}, tmp_path / "m.pt")
    sonuc = ornek_uret.main(["--model", str(tmp_path / "m.pt"), "--tokenizer", str(tmp_path / "tok.json"),
                             "--tur", "kart", "--adet", "3", "--uzunluk", "20", "--cihaz", "cpu",
                             "--cikti", str(tmp_path / "k.jsonl")])
    assert len(sonuc) == 3 and all(k["gecerli"] is False for k in sonuc)
    assert all(k["metin"].startswith("<yonetim:") for k in sonuc)    # istem çıktıda duruyor
    assert len((tmp_path / "k.jsonl").read_text(encoding="utf-8").splitlines()) == 3
    hikaye = ornek_uret.main(["--model", str(tmp_path / "m.pt"), "--tokenizer", str(tmp_path / "tok.json"),
                              "--tur", "hikaye", "--adet", "1", "--uzunluk", "10", "--baslangic", "Köyün", "--cihaz", "cpu"])
    assert hikaye[0]["metin"].startswith("Köyün")
    assert json.dumps(hikaye, ensure_ascii=False)
