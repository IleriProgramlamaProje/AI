# filtre/ (1. hafta)
- `filtre.py`: ham üretimi temizler, kaç tanesinin neden atıldığını raporlar
- `kurallar.py`: uzunluk, yasak kelime, aşırı nadir kelime (yumuşak sınır), tekrar, biçim
- `duzenle.py`: şu an kullanılan temizlik (`python ai/filtre/duzenle.py <veri klasörü>`). `ham/` ve `altin/` okur, `temiz/` ve `silindi/` yazar, girdileri değiştirmez; elenen her kaydın sebebi `silindi/` içinde. Test: `ai/testler/test_duzenle.py`

`filtre.py` (S1) gelene kadar temiz verinin tamamı `duzenle.py`'den geçer. Sınırlar ve açık kararlar: `kararlar.md` 7 Kasım.
