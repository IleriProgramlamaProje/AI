# Testler

AI depo kökünde `python -m pytest ai/testler -q` çalıştırılır.

Mevcut testler: torba boyutları, malzeme kuralları (kelime türleri), konu dağılımı, prompt biçimi ve değişen örnek, üretim ve devam, sabit tohumda tekrarın önlenmesi, bozuk dosya/uyuşmayan üretim ayarları, eski kayıt sürümü, eksik/boş motor çıktısı ve belge yolu seçimi.

`test_filtre.py` ve `test_kart_bicimi.py` görevlerle (S1, S2) birlikte yazılacak.

Motor sahtedir; gerçek öğretmen, GPU belleği veya dil kalitesini doğrulamaz. Doğrulayıcı (oyun tarafı) testleri kodu yazılınca eklenecek.
