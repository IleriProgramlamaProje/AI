"""Tokenizer eğitimi (görev M5). BPE, Hugging Face `tokenizers` kütüphanesiyle.

    python -m ai.tokenizer.egit_tokenizer --girdi <veri>/filtre/temiz/*.jsonl data/edebiyat/bilgem/bilgem.txt data/edebiyat/*.txt
    python -m ai.tokenizer.egit_tokenizer --girdi ... --boyut 8000 --hf-depo IleriProgramlamaProje/kaydir-tokenizer

Girdi dosyaları:
  *.jsonl : her satır bir kayıt. Hikâyede metin `cikti` alanında. Kartta S1'in temiz kaydındaki `kart` sözlüğü
            kart_bicimi.egitim_metni ile etiketli metne çevrilir (hazirla.py ile aynı). `kart` alanı olmayan
            ham kart kayıtları (satırlı `cikti`) atlanır; eski `egitim` alanı varsa o kullanılır.
  *.txt   : belgeler arasında boş satır (altın setin eğitim metni ya da hazır edebiyat verisi).

Kararlar (Pazar gözden geçir):
  - Kelime dağarcığı 8000 (küçük modeller için; --boyut ile değişir).
  - Büyük/küçük harf korunur. Normalizasyon: NFC (Türkçe harfler tek karakter olsun) + tırnak/kesme/tire tek biçim
    (“ ” « » → ", ’ ‘ ´ ` → ', — – → -). Normalizer tokenizer'ın içinde olduğu için eğitimde de oyunda da kendiliğinden uygulanır.
  - Saray kartının <istiyor:sol|sag|belirsiz> etiketi sözlükte var; veri onu içersin içermesin aynı tokenizer kullanılır
    (hazirla.py --istedigi). Ayrıca 20 boş <yedek_N> etiketi ayrılmıştır: dondurulduktan sonra yeni etiket gerekirse
    tokenizer.json'da bir yedeğin adı değiştirilir, token numaraları kaymaz.
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

from tokenizers import AddedToken, Regex, Tokenizer, decoders, models, normalizers, pre_tokenizers, trainers

from ai.ortak.ayarlar import GOSTERGELER, KOK
from ai.ortak.kart_bicimi import ISTEDIGI_ETIKET, UNVAN_ANAHTAR, egitim_metni

CIKTI = KOK / "ai" / "tokenizer" / "cikti" / "tokenizer.json"
SON = "<|son|>"
TEMEL = ["<pad>", "<unk>", SON]


SATIR_BASI = ["<kart>", "</kart>", "<sol>", "<sag>", "<sonuc>", "{hitap}"]   # boşluk yutmaz
YEDEK_SAYISI = 20
# Aynı işaretin farklı yazılışları tek biçime: model hepsini ayrı ayrı öğrenmesin, sözlükte yer kaplamasın.
DUZ_ISARETLER = [("[“”„‟«»″]", '"'), ("[’‘‛´`′]", "'"), ("[—–―]", "-")]


def kart_etiketleri():
    """Bölünmemesi gereken bütün etiketler. Sıra sabit: token numaraları hep aynı çıkar."""
    etkiler = [f"<{g}{i}>" for g in GOSTERGELER.values() for i in ("+", "++", "+++", "-", "--", "---")]
    durumlar = [f"<{g}:{v}>" for g in GOSTERGELER.values() for v in range(0, 101, 5)]
    konusanlar = [f"<konuşan:{a}>" for a in UNVAN_ANAHTAR.values()]
    istekler = [f"<istiyor:{e}>" for e in ISTEDIGI_ETIKET.values()]
    return SATIR_BASI + ["<konu:"] + etkiler + durumlar + konusanlar + istekler


def yedek_etiketler():
    """Boş, kullanılmayan etiketler. Sözlüğün en sonunda değil, özel tokenların arasında: numaraları sabit."""
    return [f"<yedek_{i}>" for i in range(YEDEK_SAYISI)]


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
                if k.get("tur") == "kart":
                    metin = egitim_metni(k["kart"], k["malzeme"]) if "kart" in k else k.get("egitim", "")
                else:
                    metin = k.get("cikti", "")
                if metin.strip() and "[BOŞ ÇIKTI]" not in metin:
                    yield metin.strip()
        else:
            for parca in open(yol, encoding="utf-8").read().split("\n\n"):
                if parca.strip():
                    yield parca.strip()


def bos_tokenizer():
    tok = Tokenizer(models.BPE(unk_token="<unk>"))
    tok.normalizer = normalizers.Sequence([normalizers.NFC()] +
                                          [normalizers.Replace(Regex(desen), yeni) for desen, yeni in DUZ_ISARETLER])
    # Metaspace: boşluk "▁" olur ve kelimenin başına yapışır (SentencePiece gibi); Türkçe harfler okunur kalır.
    tok.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Metaspace(prepend_scheme="first"), pre_tokenizers.Punctuation()])
    tok.decoder = decoders.Metaspace(prepend_scheme="first")
    return tok


def egit(dosyalar, boyut=8000):
    tok = bos_tokenizer()
    ozel = ([AddedToken(t, special=True, normalized=False) for t in TEMEL] + [_ozel(e) for e in kart_etiketleri()]
            + [AddedToken(e, special=True, normalized=False) for e in yedek_etiketler()])
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
