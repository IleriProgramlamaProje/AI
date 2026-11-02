"""Öğretmen modelle toplu hikâye/kart üretir ve JSONL dosyasına yazar.

Colab'da kullanım (uretim.ipynb bunu yapar):
    python -m ai.veri_uretimi.uretici --tur hikaye --adet 2000 --cikti /content/drive/MyDrive/kaydir_veri/ham/hikaye_mert.jsonl

- Her satır bir kayıt: {"surum", "id", "tur", "malzeme", "prompt", "cikti", "model", "motor", "tohum", "token", "saniye"}
- Dosya zaten varsa kaldığı yerden devam eder (Colab koparsa sorun değil).
- Motorlar: "vllm" (hızlı, toplu), "transformers" (yedek), "transformers4bit" (12B'yi tek T4'e sığdırır;
  yazımı biraz bozar, filtre ayıklamalı), "transformers8bit" (2 GPU'lu Kaggle'da 12B, daha temiz). "auto" önce vllm'i dener.
  "gemini": Google Gemini API (GPU gerekmez; anahtar GEMINI_API_KEY ortam değişkeninde, `pip install google-genai`).
- Defterde model bir kez açılıp `motor=` ile iki tür için kullanılabilir.
"""
import argparse
import json
import os
import random
import re
import time
from pathlib import Path

from ai.ortak.ayarlar import OGRETMEN_MODEL
from ai.veri_uretimi.istek_olusturucu import prompt_olustur
from ai.veri_uretimi.torbalar import EKSTRA, malzeme_cek, torbalari_yukle

KAYIT_SURUMU = 3  # 3: satırlı kart promptu, değişen örnek, kartta 2 / hikâyede 3 kelime (1 Kasım)
URETIM_AYARI = {"temperature": 0.6, "top_p": 0.95, "max_tokens": 400}  # 0.8'de 12B harfleri daha çok bozdu


# ---------------------------------------------------------------- motorlar
BOS_CIKTI = "[BOŞ ÇIKTI]"  # tolerans açıkken üretilemeyen istek; filtre bunu eler
_DUSUNCE = re.compile(r"^\s*thought(?=\s|[A-ZÇĞİÖŞÜ])\s*")    # Gemma 4 bazen düşünme kapalıyken de "thought" etiketi bırakıyor


def temizle(metin):
    return _DUSUNCE.sub("", metin).strip()


class VllmMotor:
    """vLLM: yüzlerce isteği aynı anda işler, Colab'da en hızlısı."""

    def __init__(self, model):
        from vllm import LLM, SamplingParams
        self.llm = LLM(model=model, dtype="half", max_model_len=2048, gpu_memory_utilization=0.90)
        self.ayar = SamplingParams(temperature=URETIM_AYARI["temperature"], top_p=URETIM_AYARI["top_p"],
                                   max_tokens=URETIM_AYARI["max_tokens"])

    def uret(self, promptlar):
        mesajlar = [[{"role": "user", "content": p}] for p in promptlar]
        ciktilar = self.llm.chat(mesajlar, self.ayar, use_tqdm=False,
                                 chat_template_kwargs={"enable_thinking": False})
        return [(temizle(o.outputs[0].text), len(o.outputs[0].token_ids)) for o in ciktilar]


class TransformersMotor:
    """Yedek motor: daha yavaş ama her yerde çalışır. bit=4/8: büyük modeli küçük GPU'ya sığdırır."""

    def __init__(self, model, bit=None):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model)
        self.tok.padding_side = "left"
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        ayar = {"torch_dtype": torch.float16, "device_map": "auto"}
        if bit in (4, 8):
            from transformers import BitsAndBytesConfig
            ayar["quantization_config"] = (BitsAndBytesConfig(load_in_8bit=True) if bit == 8 else
                                           BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                              bnb_4bit_compute_dtype=torch.float16))
        try:
            self.model = AutoModelForCausalLM.from_pretrained(model, **ayar)
        except (ValueError, KeyError):  # Gemma 4 çok kipli: bazı sürümlerde bu sınıfla yüklenir
            from transformers import AutoModelForImageTextToText
            self.model = AutoModelForImageTextToText.from_pretrained(model, **ayar)

    def uret(self, promptlar):
        metinler = [self.tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False,
                                                 add_generation_prompt=True, enable_thinking=False)
                    for p in promptlar]
        girdi = self.tok(metinler, return_tensors="pt", padding=True, add_special_tokens=False).to(self.model.device)
        with self.torch.no_grad():
            cikti = self.model.generate(**girdi, do_sample=True, temperature=URETIM_AYARI["temperature"],
                                        top_p=URETIM_AYARI["top_p"], max_new_tokens=URETIM_AYARI["max_tokens"],
                                        pad_token_id=self.tok.pad_token_id,
                                        remove_invalid_values=True)  # T4'te fp16 taşmasında çökmesin
        yeni = cikti[:, girdi["input_ids"].shape[1]:]
        sonuc = []
        for satir in yeni:
            uzunluk = int((satir != self.tok.pad_token_id).sum())
            sonuc.append((temizle(self.tok.decode(satir, skip_special_tokens=True)), uzunluk))
        return sonuc


GEMINI_MODEL = "gemini-flash-latest"   # Google'ın güncel Flash modeline giden takma ad; defterde değiştirilebilir


class GeminiMotor:
    """Gemini API: istekler paralel gönderilir. Kota/hız sınırında (429, 503) bekleyip yeniden dener."""

    def __init__(self, model=GEMINI_MODEL, istemci=None, paralel=8, bekleme=(10, 20, 40, 60, 60)):
        if istemci is None:
            from google import genai
            anahtar = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if not anahtar:
                raise RuntimeError("GEMINI_API_KEY ortam değişkeni yok (Colab/Kaggle Secrets'a ekleyin)")
            istemci = genai.Client(api_key=anahtar)
        self.istemci, self.model, self.paralel, self.bekleme = istemci, model, paralel, bekleme
        self.dusunme_kapat = True   # model düşünme bütçesini desteklemiyorsa bir kez denenip kapatılır

    def _ayar(self):
        ayar = {"temperature": URETIM_AYARI["temperature"], "top_p": URETIM_AYARI["top_p"],
                "max_output_tokens": URETIM_AYARI["max_tokens"]}
        if self.dusunme_kapat:
            ayar["thinking_config"] = {"thinking_budget": 0}
        return ayar

    def _tek(self, prompt):
        for i in range(len(self.bekleme) + 1):
            try:
                yanit = self.istemci.models.generate_content(model=self.model, contents=prompt, config=self._ayar())
                metin = temizle(getattr(yanit, "text", None) or "")
                kullanim = getattr(yanit, "usage_metadata", None)
                token = int(getattr(kullanim, "candidates_token_count", 0) or 0)
                return metin, token
            except Exception as hata:
                ileti = str(hata)
                if self.dusunme_kapat and "thinking" in ileti.lower():
                    self.dusunme_kapat = False      # bu model düşünme ayarını kabul etmiyor
                    continue
                if i < len(self.bekleme) and any(k in ileti for k in ("429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE")):
                    time.sleep(self.bekleme[i])
                    continue
                raise

    def uret(self, promptlar):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(self.paralel, len(promptlar))) as havuz:
            return list(havuz.map(self._tek, promptlar))


MOTORLAR = ("auto", "vllm", "transformers", "transformers4bit", "transformers8bit", "gemini")


def motor_ac(ad, model=OGRETMEN_MODEL):
    if ad not in MOTORLAR:
        raise ValueError(f"Bilinmeyen motor: {ad}")
    if ad == "gemini":
        return GeminiMotor(GEMINI_MODEL if model == OGRETMEN_MODEL else model), ad
    if ad in ("transformers4bit", "transformers8bit"):
        return TransformersMotor(model, bit=4 if ad.endswith("4bit") else 8), ad
    if ad in ("auto", "vllm"):
        try:
            return VllmMotor(model), "vllm"
        except Exception as hata:  # vllm kurulu değil ya da bu modeli desteklemiyor
            if ad == "vllm":
                raise
            print(f"vLLM açılamadı ({hata.__class__.__name__}: {hata}); transformers ile devam.")
    return TransformersMotor(model), "transformers"


# ---------------------------------------------------------------- üretim
def mevcut_sayi(yol, tur=None, model=None, tohum=None):
    """Devam etmeden dosyayı denetle; bozuk kaydı sessizce atlama."""
    if not yol.exists():
        return 0
    sayi = 0
    with open(yol, encoding="utf-8") as f:
        for sayi, satir in enumerate(f, 1):
            try:
                kayit = json.loads(satir)
                if not isinstance(kayit, dict):
                    raise ValueError("Kayıt nesne olmalı")
                if tur is not None and (kayit.get("tur") != tur or
                        kayit.get("id") != f"{tur}-{sayi:07d}"):
                    raise ValueError("Tür veya kayıt sırası uyuşmuyor")
                if model is not None and kayit.get("model") != model:
                    raise ValueError("Model uyuşmuyor")
                if tur is not None and kayit.get("surum") != KAYIT_SURUMU:
                    raise ValueError("Eski kayıt biçimi; yeni çıktı dosyası seçin")
                if tur is not None and kayit.get("tohum") != tohum:
                    raise ValueError("Tohum uyuşmuyor")
                if not isinstance(kayit.get("cikti"), str) or not kayit["cikti"].strip():
                    raise ValueError("Çıktı boş veya metin değil")
                if not satir.endswith("\n"):
                    raise ValueError("Son satır tamamlanmamış; satır sonunu kontrol edin")
            except (ValueError, TypeError) as hata:
                raise ValueError(f"{yol}, satır {sayi}: {hata}") from hata
    return sayi


def son_satiri_onar(yol):
    """Kesintide yarım kalan son satırı keser (Colab koptuğunda olur). Sadece son satıra dokunur."""
    yol = Path(yol)
    if not yol.exists() or yol.stat().st_size == 0:
        return False
    veri = yol.read_bytes()
    son_nl = veri.rfind(b"\n", 0, len(veri) - 1) + 1 if veri.endswith(b"\n") else veri.rfind(b"\n") + 1
    son = veri[son_nl:]
    try:
        json.loads(son.decode("utf-8"))
        if not veri.endswith(b"\n"):        # kayıt tam, sadece satır sonu eksik
            with open(yol, "ab") as f:
                f.write(b"\n")
        return False
    except (ValueError, UnicodeDecodeError):
        pass
    with open(yol, "r+b") as f:
        f.truncate(son_nl)
    print(f"Uyarı: {yol.name} dosyasının yarım kalan son satırı silindi (kesinti).")
    return True


def _gecerli(c):
    return isinstance(c, (tuple, list)) and len(c) == 2 and isinstance(c[0], str) and c[0].strip()


def _guvenli_uret(motor, promptlar):
    """Grup hata verirse bir kez daha dener; yalnız başarısız olanları tek tek yeniden dener; olmayan BOS_CIKTI olur."""
    sonuc = [None] * len(promptlar)
    for _ in range(2):
        try:
            g = motor.uret(promptlar)
            if len(g) == len(promptlar):
                sonuc = [c if _gecerli(c) else None for c in g]
                break
        except Exception as hata:  # GPU/fp16 hatası tüm geceyi durdurmasın
            print(f"Grup hatası ({hata.__class__.__name__}: {hata}); tekrar deneniyor.")
    for i, c in enumerate(sonuc):
        if c is None:
            try:
                tek = motor.uret([promptlar[i]])[0]
                sonuc[i] = tek if _gecerli(tek) else (BOS_CIKTI, 0)
            except Exception:
                sonuc[i] = (BOS_CIKTI, 0)
    return sonuc


def uret(tur, adet, cikti, motor_adi="auto", grup=64, tohum=None, model=OGRETMEN_MODEL, motor=None,
         tolerans=False, onar=False, bitis=None):
    """`adet` kayda ulaşana kadar üretir; her grup bitince dosyaya ekler.
    tolerans=True: hatalı/boş çıktı geceyi durdurmaz (BOS_CIKTI yazılır, filtre eler).
    onar=True: kesintide yarım kalan son satır silinip devam edilir. Defter ikisini de açar.
    bitis: bu zamandan (time.time()) sonra yeni grup başlatılmaz; kalan iş dosyada, sonra devam edilir.
    Art arda 3 grubun hepsi boş çıkarsa (kalıcı GPU hatası) durur; boş grupları dosyaya yazmaz."""
    if tur not in EKSTRA:
        raise ValueError(f"Bilinmeyen tür: {tur}")
    if adet < 0 or grup <= 0:
        raise ValueError("adet negatif olamaz; grup pozitif olmalı")
    cikti = Path(cikti)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    if onar:
        son_satiri_onar(cikti)
    baslangic = mevcut_sayi(cikti, tur, model, tohum)
    if baslangic >= adet:
        print(f"{cikti.name} zaten {baslangic} kayıt içeriyor, üretilecek bir şey yok.")
        return
    rng = random.Random(tohum if tohum is not None else time.time_ns())
    torbalar = torbalari_yukle()
    # Sabit tohumla devam ederken önceki malzemeleri yeniden üretme.
    if tohum is not None:
        for _ in range(baslangic):
            malzeme_cek(torbalar, tur, rng)
    if motor is None:
        motor, motor_adi = motor_ac(motor_adi, model)
    print(f"Motor: {motor_adi} · {baslangic} kayıttan devam, hedef {adet}")

    toplam_token, toplam_sure, sayac = 0, 0.0, baslangic
    with open(cikti, "a", encoding="utf-8") as f:
        bos_seri = 0
        while sayac < adet:
            if bitis is not None and time.time() > bitis:
                print(f"Süre doldu: {sayac}/{adet}. Kalanı sonraki çalıştırmada devam eder.")
                break
            n = min(grup, adet - sayac)
            durum = rng.getstate()             # grup tamamen boş çıkarsa aynı malzemeler yeniden denenir
            malzemeler = [malzeme_cek(torbalar, tur, rng) for _ in range(n)]
            promptlar = [prompt_olustur(m, torbalar) for m in malzemeler]
            t0 = time.perf_counter()
            sonuclar = _guvenli_uret(motor, promptlar) if tolerans else motor.uret(promptlar)
            if tolerans and all(m == BOS_CIKTI for m, _ in sonuclar):
                bos_seri += 1
                if bos_seri >= 3:
                    raise RuntimeError("Art arda 3 grup boş çıktı: model/GPU kalıcı hata veriyor. Çalışma zamanını yeniden başlatın.")
                rng.setstate(durum)            # devam ederken malzeme sırası kaymasın
                continue                       # boş grup yazılmaz; sayaç ilerlemez
            bos_seri = 0
            sure = max(time.perf_counter() - t0, 1e-9)
            if len(sonuclar) != n:
                raise ValueError(f"Motor {n} istek için {len(sonuclar)} çıktı döndürdü")
            if any(not isinstance(metin, str) or not metin.strip() or
                   not isinstance(token, int) or token < 0 for metin, token in sonuclar):
                raise ValueError("Motor boş/geçersiz çıktı veya token sayısı döndürdü")
            satirlar = []
            for m, p, (metin, token) in zip(malzemeler, promptlar, sonuclar):
                sayac += 1
                kayit = {"surum": KAYIT_SURUMU, "id": f"{tur}-{sayac:07d}", "tur": tur, "malzeme": m.sozluk(), "prompt": p,
                         "cikti": metin, "model": model, "motor": motor_adi, "tohum": tohum, "token": token,
                         "saniye": round(sure / n, 3)}
                satirlar.append(json.dumps(kayit, ensure_ascii=False) + "\n")
            f.write("".join(satirlar))   # grup tek seferde yazılır: kesintide en fazla son satır yarım kalır
            f.flush()
            os.fsync(f.fileno())
            toplam_token += sum(t for _, t in sonuclar)
            toplam_sure += sure
            hiz = (sayac - baslangic) / toplam_sure * 3600
            print(f"{sayac}/{adet} · {toplam_token / toplam_sure:.0f} token/sn · saatte ~{hiz:.0f} {tur}")


def main():
    ap = argparse.ArgumentParser(description="Öğretmen modelle toplu veri üretimi")
    ap.add_argument("--tur", choices=["hikaye", "kart"], required=True)
    ap.add_argument("--adet", type=int, required=True)
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--motor", choices=list(MOTORLAR), default="auto")
    ap.add_argument("--grup", type=int, default=64, help="Bir seferde kaç istek (transformers için 8-16 önerilir)")
    ap.add_argument("--tohum", default=None, help="Kişiye/ortama özel bir metin (ör. mert-colab-hikaye)")
    ap.add_argument("--model", default=OGRETMEN_MODEL)
    a = ap.parse_args()
    uret(a.tur, a.adet, a.cikti, a.motor, a.grup, a.tohum, a.model)


if __name__ == "__main__":
    main()
