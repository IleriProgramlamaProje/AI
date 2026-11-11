"""Tokenizer eğitimi (görev M5). BPE, Hugging Face `tokenizers` kütüphanesiyle.

    python -m ai.tokenizer.egit_tokenizer --girdi ~/Downloads/kaydir_veri/ham/hikaye_*.jsonl
    python -m ai.tokenizer.egit_tokenizer --girdi ... --boyut 8000 --hf-depo IleriProgramlamaProje/kaydir-tokenizer

Girdi dosyaları:
  *.jsonl : her satır bir kayıt, metin `cikti` alanında (öğretmen ham dosyası ya da S1'in temiz dosyası).
            Kart kaydında `cikti` satırlıdır (Metin:/Sol:...); onu eğitim biçimine çevirmek S1 + S2'nin işi,
            bu yüzden tur == "kart" olan ham kayıtlar atlanır. Temiz kart dosyasında `egitim` alanı varsa o kullanılır.
  *.txt   : belgeler arasında boş satır (altın setin eğitim metni ya da hazır edebiyat verisi).

Kararlar (Pazar gözden geçir):
  - Kelime dağarcığı 8000 (küçük modeller için; --boyut ile değişir).
  - Büyük/küçük harf korunur, sadece NFC normalizasyonu (Türkçe harfler tek karakter olsun).
  - Kart etiketleri ÖZEL token: hiçbir zaman bölünmez. Durum etiketleri (<para:50>) 0-100 arası 5'in katları için tek token;
    konu serbest metin olduğu için <konu: ve > ayrı, aradaki konu normal bölünür.
  - Her belgenin sonuna <|son|> eklenir (O1 belgeleri birleştirirken ayırıcı olarak kullanır).
  - Noktalama ayrı token ("istiyor." -> "▁istiyor" "."), yoksa her kelimenin noktalı/virgüllü hâli ayrı öğrenilir.
  - Satır ortasındaki etiketler (<halk++>, <para:25>, <konuşan:…>) solundaki boşluğu yutar (lstrip); yoksa her boşluk ayrı
    bir "▁" token'ı olur (örnek durum satırı bununla 13 token'dan 10'a indi). Bedeli: çözünce (decode) "aç<halk++><para->" gibi
    boşluksuz çıkar; metinden_karta bunu okur. Satır başı etiketleri (<kart>, <sol>…) ve {hitap} boşluk yutmaz.
"""
import argparse
import json
from pathlib import Path

from tokenizers import AddedToken, Tokenizer, decoders, models, normalizers, pre_tokenizers, trainers

from ai.ortak.ayarlar import GOSTERGELER, KOK
from ai.ortak.kart_bicimi import UNVAN_ANAHTAR

CIKTI = KOK / "ai" / "tokenizer" / "cikti" / "tokenizer.json"
SON = "<|son|>"
TEMEL = ["<pad>", "<unk>", SON]


SATIR_BASI = ["<kart>", "</kart>", "<sol>", "<sag>", "<sonuc>", "{hitap}"]   # boşluk yutmaz


def kart_etiketleri():
    """Bölünmemesi gereken bütün etiketler. Sıra sabit: token numaraları hep aynı çıkar."""
    etkiler = [f"<{g}{i}>" for g in GOSTERGELER.values() for i in ("+", "++", "+++", "-", "--", "---")]
    durumlar = [f"<{g}:{v}>" for g in GOSTERGELER.values() for v in range(0, 101, 5)]
    konusanlar = [f"<konuşan:{a}>" for a in UNVAN_ANAHTAR.values()]
    return SATIR_BASI + ["<konu:"] + etkiler + durumlar + konusanlar


def _ozel(e):
    ilk = f"<{next(iter(GOSTERGELER.values()))}:"
    yutar = e not in SATIR_BASI and not e.startswith(ilk)
    return AddedToken(e, special=True, lstrip=yutar, normalized=False)


def belgeler(dosyalar):
    """Dosyalardan belge metinlerini sırayla verir (boş ve [BOŞ ÇIKTI] kayıtlar atlanır)."""
    for yol in map(Path, dosyalar):
        if yol.suffix == ".jsonl":
            for satir in open(yol, encoding="utf-8"):
                if not satir.strip():
                    continue
                k = json.loads(satir)
                metin = k.get("egitim") or ("" if k.get("tur") == "kart" else k.get("cikti", ""))
                if metin.strip() and "[BOŞ ÇIKTI]" not in metin:
                    yield metin.strip()
        else:
            for parca in open(yol, encoding="utf-8").read().split("\n\n"):
                if parca.strip():
                    yield parca.strip()


def bos_tokenizer():
    tok = Tokenizer(models.BPE(unk_token="<unk>"))
    tok.normalizer = normalizers.NFC()
    # Metaspace: boşluk "▁" olur ve kelimenin başına yapışır (SentencePiece gibi); Türkçe harfler okunur kalır.
    tok.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Metaspace(prepend_scheme="first"), pre_tokenizers.Punctuation()])
    tok.decoder = decoders.Metaspace(prepend_scheme="first")
    return tok


def egit(dosyalar, boyut=8000):
    tok = bos_tokenizer()
    ozel = [AddedToken(t, special=True, normalized=False) for t in TEMEL] + [_ozel(e) for e in kart_etiketleri()]
    trainer = trainers.BpeTrainer(vocab_size=boyut, min_frequency=2, special_tokens=ozel, show_progress=True)
    tok.train_from_iterator((b + " " + SON for b in belgeler(dosyalar)), trainer=trainer)
    return tok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--girdi", nargs="+", required=True, help="jsonl / txt dosyaları")
    ap.add_argument("--boyut", type=int, default=8000, help="kelime dağarcığı (vocab) boyutu")
    ap.add_argument("--cikti", default=str(CIKTI))
    ap.add_argument("--hf-depo", help="verilirse tokenizer.json bu Hugging Face deposuna yüklenir (HF_TOKEN gerekir)")
    a = ap.parse_args()

    adet = sum(1 for _ in belgeler(a.girdi))
    print(f"{adet} belge okunuyor…")
    tok = egit(a.girdi, a.boyut)
    Path(a.cikti).parent.mkdir(parents=True, exist_ok=True)
    tok.save(a.cikti)
    print(f"kaydedildi: {a.cikti} · kelime dağarcığı {tok.get_vocab_size()}")

    if a.hf_depo:
        from huggingface_hub import HfApi
        api = HfApi()
        api.create_repo(a.hf_depo, private=True, exist_ok=True)
        api.upload_file(path_or_fileobj=a.cikti, path_in_repo="tokenizer.json", repo_id=a.hf_depo,
                        commit_message=f"tokenizer: {adet} belge, vocab {tok.get_vocab_size()}")
        print(f"Hugging Face'e yüklendi: {a.hf_depo}")


if __name__ == "__main__":
    main()
