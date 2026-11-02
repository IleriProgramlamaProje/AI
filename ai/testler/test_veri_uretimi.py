"""Torba çekme, prompt oluşturma ve üretim döngüsünün (sahte motorla) testleri.
Çalıştırma: depo kökünde `pytest ai/testler`
"""
import json
import random

from ai.veri_uretimi import uretici
from ai.veri_uretimi.istek_olusturucu import prompt_olustur
from ai.veri_uretimi.istek_olusturucu import ORNEKLER, ornek_sec
from ai.veri_uretimi.torbalar import EKSTRA, KELIME_TURU, malzeme_cek, torbalari_yukle

T = torbalari_yukle()


def test_torba_boyutlari():
    assert len(T["kelime"]) > 1400                                   # 1 Kasım sadeleştirmesi (~1500)
    assert all(len(T["kelime_tur"][t]) > 300 for t in ("isim", "fiil", "sıfat"))
    assert len(T["karakter"]) == 23
    assert len(T["olay"]) == 200


def test_malzeme_kurali():
    rng = random.Random(1)
    for tur in ("hikaye", "kart"):
        for _ in range(200):
            m = malzeme_cek(T, tur, rng)
            turler = KELIME_TURU[tur]                              # hikâye: isim+fiil+sıfat · kart: isim+sıfat
            assert m.karakter and len(m.kelimeler) == len(turler)
            assert all(m.kelimeler[i] in T["kelime_tur"][t] for i, t in enumerate(turler))
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


def test_kart_promptu_satirli():
    # Öğretmen etiketli gövde yerine satırlı biçim yazar (karar → sonuç → etki); eğitim metnine
    # ai/ortak/kart_bicimi.py çevirir. Sabit örnekte model etkileri kopyalıyordu (ilk denemede %31).
    p = prompt_olustur(malzeme_cek(T, 'kart', random.Random(1)), T)
    for satir in ('Metin:', 'Sol:', 'Sol sonuç:', 'Sol etki:', 'Sağ:', 'Sağ sonuç:', 'Sağ etki:'):
        assert satir in p
    assert 'en az birini kullan' in p


def test_ornek_her_istekte_degisir():
    rng = random.Random(5)
    secilen = set()
    for _ in range(60):
        m = malzeme_cek(T, 'kart', rng)
        o = ornek_sec(m)
        assert o['karakter'] != m.karakter
        secilen.add(o['karakter'])
    assert len(secilen) >= 6 and len(ORNEKLER) == 8


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


def test_tolerans_ve_yarim_satir_onarimi(tmp_path, monkeypatch):
    class AraSiraBozuk:
        def __init__(self): self.n = 0
        def uret(self, promptlar):
            self.n += 1
            if self.n == 1:
                raise RuntimeError("probability tensor contains inf")      # ilk deneme çöker
            return [("" if i == 0 else "metin", 3) for i, _ in enumerate(promptlar)]
    yol = tmp_path / "t.jsonl"
    uretici.uret("kart", 3, yol, grup=3, tohum="t", motor=AraSiraBozuk(), tolerans=True)
    kayitlar = [json.loads(s) for s in yol.read_text(encoding="utf-8").splitlines()]
    assert len(kayitlar) == 3 and uretici.BOS_CIKTI in [k["cikti"] for k in kayitlar]
    yol.write_bytes(yol.read_bytes() + b'{"surum": 3, "id": "kart-00')          # kesinti: yarım satır
    uretici.uret("kart", 4, yol, grup=1, tohum="t", motor=SahteMotor(), onar=True)
    assert len(yol.read_text(encoding="utf-8").splitlines()) == 4


def test_dusunce_etiketi_temizlenir():
    assert uretici.temizle("thought\nMetin: Kuzey yolu kapandı.") == "Metin: Kuzey yolu kapandı."


def test_belge_klasoru_kucuk_harf(tmp_path, monkeypatch):
    from ai.ortak.ayarlar import belge_klasoru
    monkeypatch.delenv('PROJE_DOCS_DIR', raising=False)
    (tmp_path / 'AI').mkdir(); (tmp_path / 'docs').mkdir()
    assert belge_klasoru(tmp_path / 'AI') == tmp_path / 'docs'


def test_kalici_hata_durur_ve_sure_siniri(tmp_path):
    import pytest, time
    class HepBozuk:
        def uret(self, promptlar):
            raise RuntimeError("device-side assert")
    yol = tmp_path / "k.jsonl"
    with pytest.raises(RuntimeError, match="Art arda 3 grup"):
        uretici.uret("kart", 50, yol, grup=5, tohum="k", motor=HepBozuk(), tolerans=True)
    assert not yol.exists() or yol.read_text() == ""          # boş gruplar yazılmaz
    uretici.uret("kart", 50, yol, grup=5, tohum="k", motor=SahteMotor(), bitis=time.time() - 1)
    assert yol.read_text() == ""                               # süre dolmuşsa yeni grup başlamaz


def test_sadece_bozuk_olan_yeniden_denenir(tmp_path):
    class Sayac:
        def __init__(self): self.cagri = 0
        def uret(self, promptlar):
            self.cagri += 1
            return [("" if (len(promptlar) > 1 and i == 0) else "metin", 3) for i, _ in enumerate(promptlar)]
    m = Sayac()
    uretici.uret("kart", 8, tmp_path / "s.jsonl", grup=8, tohum="s", motor=m, tolerans=True)
    assert m.cagri == 2                                         # 1 grup + 1 tekli yeniden deneme


def test_bos_grup_sonrasi_devam_malzemeyi_tekrarlamaz(tmp_path):
    class IkinciGrupBos:
        def __init__(self): self.n = 0
        def uret(self, promptlar):
            self.n += 1
            return [("" if self.n in (2, 3) else "metin", 1) for _ in promptlar]   # 2. grup (ve tekrarı) boş
    yol, ref = tmp_path / "a.jsonl", tmp_path / "ref.jsonl"
    uretici.uret("kart", 10, yol, grup=5, tohum="r", motor=IkinciGrupBos(), tolerans=True)
    uretici.uret("kart", 20, yol, grup=5, tohum="r", motor=SahteMotor(), tolerans=True)
    uretici.uret("kart", 20, ref, grup=5, tohum="r", motor=SahteMotor())
    oku = lambda p: [json.loads(s)["malzeme"] for s in p.read_text(encoding="utf-8").splitlines()]
    assert oku(yol) == oku(ref)
