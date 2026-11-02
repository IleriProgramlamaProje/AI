# Veri üretimi

Akış: `torbalar.py` → `istek_olusturucu.py` → `uretici.py` → ham JSONL. Sonraki adımlar görev: filtre (`ai/filtre/filtre.py`, S1) ve dönüştürücü (`ai/ortak/kart_bicimi.py`, S2); bkz. `Docs/yz_gorevleri.md`.
Öğretmen: **Gemma 4 12B** (`ai/ortak/ayarlar.py`). 1 Kasım'da aynı 40 promptla E4B / 12B / Gemini karşılaştırıldı; E4B anlamsız yazdı, Gemini çıktısıyla eğitim Google kurallarına aykırı, Gemma 4 Apache 2.0.

## Kurallar (malzeme)
- **Hikâye:** karakter + 3 kelime (1 isim + 1 fiil + 1 sıfat, üçü istenir) + diğer torbalardan 1–2.
- **Kart:** karakter + 2 kelime (1 isim + 1 sıfat, en az biri istenir) + konu (~%15 serbest) + gösterge durumu.

## Promptlar (`promptlar/`)
- `hikaye.txt`: önce mantık (sorun → yapılan → sonuç), kısa açık cümle, kelimeyi zorla sokma.
- `kart.txt`: öğretmen **satırlı** biçimde yazar: `Metin / Sol / Sol sonuç / Sol etki / Sağ / Sağ sonuç / Sağ etki`. Etki sonuca bakılarak yazılır.
  Eğitimdeki etiketli biçime (`<kart> <sol> … </kart>`) `kart_bicimi.py` çevirecek (görev). Etiketli gövde istendiğinde ve tek sabit örnek verildiğinde
  model örneğin etkilerini kopyalıyordu (ilk denemede kartların %31'i).
- `kart_ornekler.json`: 8 örnek kart; her istekte farklı biri gösterilir (konuşanla aynı rol seçilmez).

## Çalıştırma
Colab ve Kaggle: `uretim.ipynb` (aynı defter, ikisinde aynı anda açılabilir). Colab'da T4 → 12B 4-bit; Kaggle'da 2×T4 → 12B 8-bit.
4-bit yazımı biraz bozar (ünlü uyumu, "Alp,in"); filtre ayıklayacak.

```sh
python -m ai.veri_uretimi.uretici --tur kart --adet 100 --grup 4 --motor transformers4bit --tohum mert-kart --cikti ham/kart.jsonl
```

`adet` dosyanın ulaşacağı toplamdır. Kayıt sürümü 3 (1 Kasım; sürüm 2 dosyalarına eklenmez, yeni dosya açın): devam etmeden tür/model/tohum/sürüm, sıra, boş çıktı ve satır sonları kontrol edilir; uyuşmazlıkta dosyaya yazılmaz.
Aynı tohumla devam önceki malzemeleri atlar (`--tohum` artık metin; eski sayısal tohumlu dosyalar "Tohum uyuşmuyor" verir).
Defter `tolerans=True` (hatalı/boş çıktı yalnız o istek için yeniden denenir, olmazsa `[BOŞ ÇIKTI]` yazılır, filtre elemeli; art arda 3 grup tamamen boşsa kalıcı hata sayılıp durur), `onar=True` (kesintide yarım kalan son satır silinir) ve `bitis=` (süre dolunca yeni grup başlamaz) ile çalışır; komut satırında bunlar kapalıdır. Torbalar veya prompt değişirse yeni dosya (yeni tohum) kullanın. Aynı dosyaya iki üretici yazmamalı;
defter dosya adına kişi + ortam (+ Kaggle'da oturum) koyar.
