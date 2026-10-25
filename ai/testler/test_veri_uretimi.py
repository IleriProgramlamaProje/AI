"""Torba çekme, prompt oluşturma ve üretim döngüsünün (sahte motorla) testleri.
Çalıştırma: depo kökünde `pytest ai/testler`
"""
import json
import random

from ai.veri_uretimi import uretici
from ai.veri_uretimi.istek_olusturucu import prompt_olustur
from ai.veri_uretimi.torbalar import EKSTRA, malzeme_cek, torbalari_yukle

T = torbalari_yukle()


def test_torba_boyutlari():
    assert len(T["kelime"]) == 2000
    assert len(T["karakter"]) == 23
    assert len(T["olay"]) == 200


def test_malzeme_kurali():
    rng = random.Random(1)
    for tur in ("hikaye", "kart"):
        for _ in range(200):
            m = malzeme_cek(T, tur, rng)
            assert m.karakter and len(m.kelimeler) == 3          # her zaman var
            secilen = [k for k in m.ekstra if m.ekstra[k] != "serbest"]
            assert 1 <= len(secilen) <= 2                          # 1-2 ekstra
            assert set(secilen) <= set(EKSTRA[tur])
            if tur == "kart":
                assert set(m.durum) == {"Yönetim", "Halk", "Para", "Ordu"}
                assert all(5 <= v <= 95 for v in m.durum.values())


def test_prompt_icerigi():
    rng = random.Random(2)
    m = malzeme_cek(T, "kart", rng)
    p = prompt_olustur(m, T)
    assert m.karakter in p and all(k in p for k in m.kelimeler)
    assert "{hitap}" in p and "{" not in p.replace("{hitap}", "")
    h = prompt_olustur(malzeme_cek(T, "hikaye", rng), T)
    assert "100-150 kelime" in h and "{" not in h


class SahteMotor:
    def uret(self, promptlar):
        return [("Bir zamanlar...", 42) for _ in promptlar]


def test_uretim_ve_devam(tmp_path, monkeypatch):
    monkeypatch.setattr(uretici, "motor_ac", lambda ad, model=None: (SahteMotor(), "sahte"))
    yol = tmp_path / "h.jsonl"
    uretici.uret("hikaye", 10, yol, grup=4, tohum=0)
    uretici.uret("hikaye", 15, yol, grup=4, tohum=0)   # kaldığı yerden devam
    satirlar = [json.loads(s) for s in yol.read_text(encoding="utf-8").splitlines()]
    assert len(satirlar) == 15 and satirlar[-1]["id"] == "hikaye-0000015"
