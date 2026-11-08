"""hazirla.py (O1): kaynaklar okunur, oran tutar, train ve val ayrıdır, .bin dosyaları yazılır.
cd AI && python -m pytest ai/testler/test_hazirla.py"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(KOK), str(KOK / "ai" / "veri_hazirlama")]
import hazirla  # noqa: E402
from ai.ortak.kart_bicimi import egitim_metni  # noqa: E402
from ai.testler.test_kart_bicimi import COBAN_KART, COBAN_MALZEME  # noqa: E402

BETIK = KOK / "ai" / "veri_hazirlama" / "hazirla.py"
HIKAYE = "Köyün kuyusu kurudu. Çiftçi Ali sabah erkenden kalktı, kazmasını aldı ve dağa yürüdü."


def _sahte(sayilar):
    kaynak = {ad: [f"{ad}-{i}" for i in range(sayilar.get(ad, 0))] for ad in hazirla.ORANLAR}
    uzunluk = {ad: [10] * len(b) for ad, b in kaynak.items()}
    return kaynak, uzunluk


def test_oran_tutar_ve_kit_kaynak_sinirlar():
    kaynak, uzunluk = _sahte({"hikaye": 100, "kart": 100, "altin": 10})
    train, val, rapor = hazirla.karistir(kaynak, uzunluk, hazirla.ORANLAR)
    # BİLGEM ve edebiyat yok: payları diğerlerine oranla dağıtılır
    assert rapor["hikaye"]["hedef_oran"] == pytest.approx(0.60 / 0.825, abs=1e-3)
    assert rapor["bilgem"]["train_token"] == 0
    # Hikâye en kıt kaynak (oranına göre): hepsi kullanılır, diğerlerinden oranı kadar alınır
    assert rapor["hikaye"]["kullanilmayan_belge"] == 0
    for ad in ("hikaye", "kart", "altin"):
        assert rapor[ad]["gercek_oran"] == pytest.approx(rapor[ad]["hedef_oran"], abs=0.02)
    assert len(train) == len(set(train)), "belge tekrar etmemeli"
    assert not set(train) & set(val), "val belgesi train'de olmamalı"
    assert sum(b.startswith("hikaye") for b in val) == 5          # her kaynağın %5'i val


def test_oran_degistirilebilir():
    kaynak, uzunluk = _sahte({"hikaye": 100, "kart": 100})
    oran = dict(hazirla.ORANLAR, hikaye=0.5, kart=0.5)
    _, _, rapor = hazirla.karistir(kaynak, uzunluk, oran)
    assert rapor["kart"]["gercek_oran"] == pytest.approx(0.5, abs=0.02)


def test_kaynaklari_oku(tmp_path):
    temiz, altin, hazir = tmp_path / "temiz", tmp_path / "altin", tmp_path / "hazir"
    for d in (temiz, altin, hazir / "bilgem", hazir / "klasik"):
        d.mkdir(parents=True)
    kayitlar = [{"tur": "hikaye", "cikti": HIKAYE},
                {"tur": "kart", "cikti": "...", "kart": COBAN_KART, "malzeme": COBAN_MALZEME}]
    (temiz / "a.jsonl").write_text("".join(json.dumps(k, ensure_ascii=False) + "\n" for k in kayitlar), encoding="utf-8")
    (altin / "altin_set_egitim.txt").write_text("birinci kart\n\nikinci kart\n", encoding="utf-8")
    (hazir / "bilgem" / "b.txt").write_text("basit hikâye\n", encoding="utf-8")
    (hazir / "klasik" / "e.txt").write_text("eski metin bir\n\neski metin iki\n", encoding="utf-8")
    kaynak = hazirla.kaynaklari_oku(temiz, altin, hazir)
    assert kaynak["hikaye"] == [HIKAYE]
    assert kaynak["kart"] == [egitim_metni(COBAN_KART, COBAN_MALZEME)]
    assert kaynak["altin"] == ["birinci kart", "ikinci kart"]
    assert kaynak["bilgem"] == ["basit hikâye"]
    assert kaynak["edebiyat"] == ["eski metin bir", "eski metin iki"]


def test_uctan_uca_bin_yazar(tmp_path):
    np = pytest.importorskip("numpy")
    pytest.importorskip("tokenizers")
    from ai.tokenizer.egit_tokenizer import SON, egit
    kart = egitim_metni(COBAN_KART, COBAN_MALZEME)
    veri = tmp_path / "veri.txt"
    veri.write_text("\n\n".join([HIKAYE] * 20 + [kart] * 5), encoding="utf-8")
    tok = egit([veri], boyut=600)
    tok.save(str(tmp_path / "tok.json"))

    temiz = tmp_path / "temiz"
    temiz.mkdir()
    kayitlar = [{"tur": "hikaye", "cikti": f"{HIKAYE} {i}."} for i in range(40)] + \
               [{"tur": "kart", "cikti": "...", "kart": COBAN_KART, "malzeme": COBAN_MALZEME} for _ in range(20)]
    (temiz / "a.jsonl").write_text("".join(json.dumps(k, ensure_ascii=False) + "\n" for k in kayitlar), encoding="utf-8")
    cikti = tmp_path / "egitim"
    subprocess.run([sys.executable, str(BETIK), str(tmp_path), "--temiz", str(temiz), "--altin", str(tmp_path / "yok"),
                    "--hazir", str(tmp_path / "yok"), "--tokenizer", str(tmp_path / "tok.json"), "--cikti", str(cikti)],
                   check=True, capture_output=True)
    rapor = json.loads((cikti / "rapor.json").read_text(encoding="utf-8"))
    train = np.fromfile(cikti / "train.bin", dtype=np.uint16)
    val = np.fromfile(cikti / "val.bin", dtype=np.uint16)
    assert len(train) == rapor["train_token"] and len(val) == rapor["val_token"]
    assert (train == tok.token_to_id(SON)).sum() == rapor["train_belge"]
    assert rapor["kaynaklar"]["hikaye"]["train_belge"] > 0 and rapor["kaynaklar"]["kart"]["train_belge"] > 0
