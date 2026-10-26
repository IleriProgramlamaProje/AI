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


def test_konu_orani():
    rng = random.Random(42)
    malzemeler = [malzeme_cek(T, 'kart', rng) for _ in range(2000)]
    assert all('konu' in m.ekstra for m in malzemeler)
    oran = sum(m.ekstra['konu'] == 'serbest' for m in malzemeler) / len(malzemeler)
    assert 0.12 < oran < 0.18


def test_kart_promptu_etiketli():
    p = prompt_olustur(malzeme_cek(T, 'kart', random.Random(1)), T)
    for etiket in ('<kart>', '<sol>', '<sag>', '<sonuc>', '</kart>'):
        assert etiket in p
    assert 'Sol sonuç:' not in p


def test_devam_malzemeleri_tekrarlamaz(tmp_path, monkeypatch):
    monkeypatch.setattr(uretici, 'motor_ac', lambda *a: (SahteMotor(), 'sahte'))
    tam, parcali = tmp_path / 'tam.jsonl', tmp_path / 'parcali.jsonl'
    uretici.uret('kart', 15, tam, grup=4, tohum=42)
    uretici.uret('kart', 10, parcali, grup=3, tohum=42)
    uretici.uret('kart', 15, parcali, grup=4, tohum=42)
    def malzemeler(p):
        return [json.loads(s)['malzeme'] for s in p.read_text().splitlines()]
    assert malzemeler(tam) == malzemeler(parcali)


def test_hatalar_dosyayi_bozmaz(tmp_path, monkeypatch):
    import pytest
    yol = tmp_path / 'veri.jsonl'
    monkeypatch.setattr(uretici, 'motor_ac', lambda *a: (SahteMotor(), 'sahte'))
    for tur, adet, grup in [('kart', 1, 0), ('kart', -1, 4), ('yanlis', 1, 4)]:
        with pytest.raises(ValueError):
            uretici.uret(tur, adet, yol, grup=grup)
        assert not yol.exists()
    uretici.uret('kart', 2, yol, tohum=7)
    once = yol.read_bytes()
    for kwargs in ({'tur': 'hikaye', 'tohum': 7}, {'tur': 'kart', 'tohum': 8},
                   {'tur': 'kart', 'tohum': 7, 'model': 'baska'}):
        with pytest.raises(ValueError):
            uretici.uret(adet=3, cikti=yol, **kwargs)
        assert yol.read_bytes() == once
    for bozuk in (b'{"id":', b'\n', once.rstrip(b'\n')):
        yol.write_bytes(bozuk)
        with pytest.raises(ValueError):
            uretici.uret('kart', 3, yol, tohum=7)
        assert yol.read_bytes() == bozuk


def test_motor_eksik_ve_bos_cikti(tmp_path, monkeypatch):
    import pytest
    class BozukMotor:
        def __init__(self, sonuc): self.sonuc = sonuc
        def uret(self, promptlar): return self.sonuc
    for i, sonuc in enumerate(([], [('metin', 1)], [('', 0), ('metin', 1)])):
        monkeypatch.setattr(uretici, 'motor_ac', lambda *a: (BozukMotor(sonuc), 'sahte'))
        yol = tmp_path / f'{i}.jsonl'
        with pytest.raises(ValueError):
            uretici.uret('kart', 2, yol, grup=2)
        assert yol.read_bytes() == b''


def test_belge_yolu(tmp_path, monkeypatch):
    from ai.ortak.ayarlar import belge_klasoru
    monkeypatch.delenv('PROJE_DOCS_DIR', raising=False)
    kok = tmp_path / 'AI'
    kok.mkdir()
    assert belge_klasoru(kok) == kok / 'docs'
    (tmp_path / 'Docs').mkdir()
    assert belge_klasoru(kok) == tmp_path / 'Docs'
    monkeypatch.setenv('PROJE_DOCS_DIR', str(tmp_path / 'ozel'))
    assert belge_klasoru(kok) == tmp_path / 'ozel'


def test_eski_kayit_surumu_reddedilir(tmp_path, monkeypatch):
    import pytest
    monkeypatch.setattr(uretici, 'motor_ac', lambda *a: (SahteMotor(), 'sahte'))
    yol = tmp_path / 'eski.jsonl'
    uretici.uret('kart', 1, yol)
    kayit = json.loads(yol.read_text())
    del kayit['surum']
    yol.write_text(json.dumps(kayit) + '\n')
    once = yol.read_bytes()
    with pytest.raises(ValueError, match='Eski kayıt biçimi'):
        uretici.uret('kart', 2, yol)
    assert yol.read_bytes() == once
