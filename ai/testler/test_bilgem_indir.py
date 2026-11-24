"""bilgem_indir.py (S3): temizlik, eleme sebepleri, masal önceliği, dosya çıktısı. İnternet gerekmez.
cd AI && python -m pytest ai/testler/test_bilgem_indir.py"""
import json
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(KOK), str(KOK / "ai" / "veri_hazirlama")]
import bilgem_indir as b  # noqa: E402

BETIK = KOK / "ai" / "veri_hazirlama" / "bilgem_indir.py"
CUMLE = "Kervan yavaşça ilerledi ve yolcular akşam olunca hanın avlusunda dinlendi. "
MASAL = "Minik tavşan ormanda annesini aradı. " + CUMLE * 20   # ~210 kelime
DUZ = "Yaşlı tüccar çarşıda kumaş sattı. " + CUMLE * 20


def test_temizle_markdown_ve_ingilizce_not():
    ham = ("## Başlık (The Title)\n\nİlk **kalın** paragraf.\n\n* madde satırı\n---\nSon *vurgulu* söz.\n\n"
           "Translation Notes & Science Integration Explanation:\nThis story explains the sky.")
    assert b.temizle(ham) == "İlk kalın paragraf.\nmadde satırı\nSon vurgulu söz."


def test_temiz_metinde_bos_satir_yok():
    assert "\n\n" not in b.temizle("Bir.\n\n\n\nİki.\n\nÜç.")


def test_eleme_sebepleri():
    def sebep(ham):
        return b.eleme_sebebi(ham, b.temizle(ham))
    assert sebep("Okay, here's a story in Turkish, written in the style of a forum post.\n\n" + DUZ) == "ingilizce"
    assert sebep("Reddit'te bir başlık gördüm. " + DUZ) == "forum"
    assert sebep("Ayşe bilgisayarını açtı. " + DUZ) == "modern"
    assert sebep("Vali konağa geldi. " + DUZ) == "modern"          # tema.json yasak kelimesi
    assert sebep("Yıl 1998 idi. " + DUZ) == "modern"
    assert sebep("Kısa bir hikâye.") == "kisa"
    assert sebep(DUZ) is None


def test_kafes_modern_sayilmaz():
    assert not b.modern_mu("kafes")
    assert b.modern_mu("fotoğrafları") and b.modern_mu("ofiste") and b.modern_mu("trenle")


def test_topla_masal_once_hedefte_durur_tekrar_sayilir():
    akis = [json.dumps({"text": t}) for t in (DUZ, MASAL, MASAL, DUZ + " Son.")] + ["bozuk satır"]
    secilen, sayim = b.topla(akis, hedef=300)
    assert sayim["okunan"] == 4 and sayim["tekrar"] == 1 and sayim["uygun"] == 3
    assert secilen[0].startswith("Minik tavşan") and len(secilen) == 2


def test_betik_yerel_girdiden_yazar(tmp_path):
    girdi = tmp_path / "g.jsonl"
    girdi.write_text("\n".join(json.dumps({"text": t}) for t in (MASAL, DUZ)) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, str(BETIK), "--girdi", str(girdi), "--cikti", str(tmp_path / "c"),
                    "--hedef", "100000"], check=True, capture_output=True)
    belgeler = (tmp_path / "c" / "bilgem.txt").read_text(encoding="utf-8").split("\n\n")
    assert [x.strip()[:12] for x in belgeler] == ["Minik tavşan", "Yaşlı tüccar"]
    assert "Apache 2.0" in (tmp_path / "c" / "KAYNAK.md").read_text(encoding="utf-8")
