"""Projenin sabitleri tek yerde. Bir değer değişince sadece burası değişir."""
from pathlib import Path

# Depo kökü: ai/ortak/ayarlar.py -> iki üst klasör
KOK = Path(__file__).resolve().parents[2]
TORBA_KLASORU = KOK / "data" / "torbalar"
TEMA_DOSYASI = KOK / "docs" / "tema.json"
PROMPT_KLASORU = KOK / "ai" / "veri_uretimi" / "promptlar"

# Göstergeler (görünen ad -> etiket adı)
GOSTERGELER = {"Yönetim": "yonetim", "Halk": "halk", "Para": "para", "Ordu": "ordu"}

# Etki işaretleri -> oyundaki sayı
ETKI_KADEMELERI = {"+": 5, "++": 10, "+++": 15, "-": -5, "--": -10, "---": -15}

# Öğretmen model (hazırlık haftasında seçildi: Gemma 4 E4B)
OGRETMEN_MODEL = "google/gemma-4-E4B-it"
