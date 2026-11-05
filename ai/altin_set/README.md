# Altın set sayfası

claude.ai'de yayında: **Altın Set Prompt Üretici** (ortak liste orada tutulur; ekibe düzenleme yetkisiyle paylaşılır).

- `sablon.html`: sayfanın kodu. Veri yerine `/*VERI*/null` yer tutucusu var.
- `sayfa_olustur.py`: torbalar + `tema.json` + kart örnekleriyle `index.html` üretir: `python -m ai.altin_set.sayfa_olustur`
- `index.html`: yayınlanan sayfa. Torbalar değişince yeniden üretilip yayınlanır.

Üstteki **Kart / Hikâye** düğmesi türü seçer; bütün sekmeler (Üret, liste, Veri) o türle çalışır.

Kart akışı: kart sayısını seç (10/20/30/50/100) → prompt'u kopyala → kendi yapay zekâna ver → cevabı yapıştır → sayfa kartları ayrıştırıp kontrol eder → hatasızları kaydet. Okuma (iyi/at) yok; kurallar otomatik kontrol edilir (`kart_formati.md` 4. bölüm, `yz_gorevleri.md` S1 kart kuralları).

İndirmeler: oyun JSON'u (3. bölüm, `kaynak: altin_set`, `lisans: sadece_ders`), eğitim metni (2. bölüm), ham JSONL (öğretmen üretimiyle aynı alanlar), CSV.

**Hikâye modu** (3 Kasım): 5/10/20/30/50 hikâyelik paket. Her hikâyenin malzemesi `hikaye.txt` ile aynı: karakter + 3 kelime (isim + fiil + sıfat) + olay/yer/zaman/ruh hâli/özellik/anlatımdan 1–2. Model her hikâyenin başına `HİKÂYE n · Karakter: … · Kelimeler: …` satırını geri yazar.
Otomatik kontrol (`yz_gorevleri.md` hikâye kuralları): 70–200 kelime (100–150 dışı uyarı), üç kelimenin üçü de geçmeli (ek/çekim kabul), modern kelime yok, süslü parantez yok, tekrar yok.
Kayıt ayrı listede (`hikayeler3`). İndirmeler: eğitim metni (hikâyeler düz metin, aralarında boş satır), ham JSONL (`tur: hikaye`, öğretmen üretimiyle aynı alanlar), CSV.
