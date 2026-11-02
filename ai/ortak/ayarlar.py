"""Projenin sabitleri tek yerde. Bir değer değişince sadece burası değişir."""
import os
from pathlib import Path

# Depo kökü: ai/ortak/ayarlar.py -> iki üst klasör
KOK = Path(__file__).resolve().parents[2]
TORBA_KLASORU = KOK / "data" / "torbalar"
# Ayrı depolar varsayılan olarak kardeş klasörlerdir; sembolik bağlantı gerekmez.
# Eski tek-depo düzeni de desteklenir. Özel konum ortam değişkeniyle seçilir.
def belge_klasoru(kok=KOK):
    if os.environ.get("PROJE_DOCS_DIR"):
        return Path(os.environ["PROJE_DOCS_DIR"]).expanduser().resolve()
    for ad in ("Docs", "docs"):      # GitHub adı Docs; git clone yerelde küçük harfle de açabilir
        kardes = kok.parent / ad
        if kardes.is_dir() and kardes.resolve() != (kok / "docs").resolve():
            return kardes
    return kok / "docs"


TEMA_DOSYASI = belge_klasoru() / "tema.json"
PROMPT_KLASORU = KOK / "ai" / "veri_uretimi" / "promptlar"

# Göstergeler (görünen ad -> etiket adı)
GOSTERGELER = {"Yönetim": "yonetim", "Halk": "halk", "Para": "para", "Ordu": "ordu"}

# Etki işaretleri -> oyundaki sayı
ETKI_KADEMELERI = {"+": 5, "++": 10, "+++": 15, "-": -5, "--": -10, "---": -15}

# Öğretmen model (1 Kasım: aynı 40 promptla karşılaştırma sonrası Gemma 4 12B; E4B elendi)
OGRETMEN_MODEL = "google/gemma-4-12B-it"
