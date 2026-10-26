# AI · Kaydır & Karar Ver

Türkçe kart oyununun veri üretimi ve model geliştirme deposu. Oyun istemcisi [Game](https://github.com/IleriProgramlamaProje/Game), ortak belgeler [Docs](https://github.com/IleriProgramlamaProje/Docs) deposundadır. Üç depoyu aynı klasöre klonlayın.

Python 3.11 ortamında, bu deponun kökünden:

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r ai/requirements.txt
python -m pytest ai/testler -q
```

Kod kardeş `../Docs/tema.json` dosyasını bulur; eski `docs/` yolu da desteklenir. Farklı yerleşim için `PROJE_DOCS_DIR` değişkenini Docs klasörüne ayarlayın. Sembolik bağlantı zorunlu değildir.

Mevcut kod: torbalar → prompt → öğretmen motoru → JSONL. Model, filtre, tokenizer, eğitim ve oyun sunucusu henüz uygulanmadı. `ai/` altındaki README dosyaları hedef görevleri gösterir.

Colab ve devam etme kuralları: [veri üretimi](ai/veri_uretimi/README.md). Yerel testler sahte motor kullanır; gerçek GPU üretiminin başarısını veya içerik kalitesini kanıtlamaz. Büyük çıktılar/ağırlıklar Drive veya Hugging Face'te saklanır.
