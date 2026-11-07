"""duzenle.py uçtan uca: iyi kart geçer, kısa ve tekrar eden kart sebebiyle elenir.   cd AI && python -m pytest ai/testler/test_duzenle.py"""
import json
import subprocess
import sys
from pathlib import Path

BETIK = Path(__file__).resolve().parents[1] / "filtre" / "duzenle.py"
METIN = ("Koyunlarım otlakta aç kaldı {hitap}, kuyular kurudu ve çobanlar köye dönmek istiyor. "
         "Bu kış sürü dağılırsa pazarda yün de et de bulunmaz.")


def _cikti(metin):
    return (f"Metin: {metin}\nSol: Yeni otlak aç\nSol sonuç: Sürü doydu ama hazineden para gitti.\nSol etki: Halk ++, Para -\n"
            "Sağ: Çobanları bekle\nSağ sonuç: Hazine korundu ama sürü zayıfladı.\nSağ etki: Para +, Halk --")


def _kayit(no, metin):
    return {"surum": 3, "id": f"kart-{no:07d}", "tur": "kart", "prompt": f"prompt {no}", "cikti": _cikti(metin),
            "malzeme": {"tur": "kart", "karakter": "Çoban", "kelimeler": ["otlak", "aç"], "ekstra": {"konu": "serbest"},
                        "durum": {"Yönetim": 50, "Halk": 40, "Para": 25, "Ordu": 60}},
            "model": "deneme", "motor": "sahte", "tohum": "t", "token": 1, "saniye": 0.1}


def test_duzenle_uctan_uca(tmp_path):
    (tmp_path / "ham").mkdir()
    (tmp_path / "altin").mkdir()
    kayitlar = [_kayit(1, METIN), _kayit(2, METIN), _kayit(3, "Çok kısa bir metin {hitap}.")]
    (tmp_path / "ham" / "kart_t.jsonl").write_text("".join(json.dumps(k, ensure_ascii=False) + "\n" for k in kayitlar), encoding="utf-8")
    subprocess.run([sys.executable, str(BETIK), str(tmp_path)], check=True, capture_output=True)
    temiz = (tmp_path / "temiz" / "model_ciktilari.jsonl").read_text(encoding="utf-8").splitlines()
    silinen = [json.loads(s) for s in (tmp_path / "silindi" / "model_silinenler.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(temiz) == 1
    kodlar = {k for s in silinen for k in s["sebep_kodu"]}
    assert "metin<20" in kodlar and "mukerrer" in kodlar
