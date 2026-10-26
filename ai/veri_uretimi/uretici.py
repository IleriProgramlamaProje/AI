"""Öğretmen modelle toplu hikâye/kart üretir ve JSONL dosyasına yazar.

Colab'da kullanım (uretim.ipynb bunu yapar):
    python -m ai.veri_uretimi.uretici --tur hikaye --adet 2000 --cikti /content/drive/MyDrive/ileri-programlama/02_Veri/uretilen/hikaye_01.jsonl

- Her satır bir kayıt: {"surum", "id", "tur", "malzeme", "prompt", "cikti", "model", "tohum", "token", "saniye"}
- Dosya zaten varsa kaldığı yerden devam eder (Colab koparsa sorun değil).
- İki motor: "vllm" (hızlı, toplu) ve "transformers" (yedek). "auto" önce vllm'i dener.
"""
import argparse
import json
import random
import time
from pathlib import Path

from ai.ortak.ayarlar import OGRETMEN_MODEL
from ai.veri_uretimi.istek_olusturucu import prompt_olustur
from ai.veri_uretimi.torbalar import EKSTRA, malzeme_cek, torbalari_yukle

KAYIT_SURUMU = 2  # Etiketli kart gövdesi ve devam tohumu kaydı
URETIM_AYARI = {"temperature": 0.8, "top_p": 0.95, "max_tokens": 400}


# ---------------------------------------------------------------- motorlar
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
        return [(o.outputs[0].text.strip(), len(o.outputs[0].token_ids)) for o in ciktilar]


class TransformersMotor:
    """Yedek motor: daha yavaş ama her yerde çalışır."""

    def __init__(self, model):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model)
        self.tok.padding_side = "left"
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(model, torch_dtype=torch.float16, device_map="auto")

    def uret(self, promptlar):
        metinler = [self.tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False,
                                                 add_generation_prompt=True, enable_thinking=False)
                    for p in promptlar]
        girdi = self.tok(metinler, return_tensors="pt", padding=True).to(self.model.device)
        with self.torch.no_grad():
            cikti = self.model.generate(**girdi, do_sample=True, temperature=URETIM_AYARI["temperature"],
                                        top_p=URETIM_AYARI["top_p"], max_new_tokens=URETIM_AYARI["max_tokens"],
                                        pad_token_id=self.tok.pad_token_id)
        yeni = cikti[:, girdi["input_ids"].shape[1]:]
        sonuc = []
        for satir in yeni:
            uzunluk = int((satir != self.tok.pad_token_id).sum())
            sonuc.append((self.tok.decode(satir, skip_special_tokens=True).strip(), uzunluk))
        return sonuc


def motor_ac(ad, model=OGRETMEN_MODEL):
    if ad not in ("auto", "vllm", "transformers"):
        raise ValueError(f"Bilinmeyen motor: {ad}")
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


def uret(tur, adet, cikti, motor_adi="auto", grup=64, tohum=None, model=OGRETMEN_MODEL):
    """`adet` kayda ulaşana kadar üretir; her grup bitince dosyaya ekler."""
    if tur not in EKSTRA:
        raise ValueError(f"Bilinmeyen tür: {tur}")
    if adet < 0 or grup <= 0:
        raise ValueError("adet negatif olamaz; grup pozitif olmalı")
    cikti = Path(cikti)
    cikti.parent.mkdir(parents=True, exist_ok=True)
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
    motor, motor_adi = motor_ac(motor_adi, model)
    print(f"Motor: {motor_adi} · {baslangic} kayıttan devam, hedef {adet}")

    toplam_token, toplam_sure, sayac = 0, 0.0, baslangic
    with open(cikti, "a", encoding="utf-8") as f:
        while sayac < adet:
            n = min(grup, adet - sayac)
            malzemeler = [malzeme_cek(torbalar, tur, rng) for _ in range(n)]
            promptlar = [prompt_olustur(m, torbalar) for m in malzemeler]
            t0 = time.perf_counter()
            sonuclar = motor.uret(promptlar)
            sure = max(time.perf_counter() - t0, 1e-9)
            if len(sonuclar) != n:
                raise ValueError(f"Motor {n} istek için {len(sonuclar)} çıktı döndürdü")
            if any(not isinstance(metin, str) or not metin.strip() or
                   not isinstance(token, int) or token < 0 for metin, token in sonuclar):
                raise ValueError("Motor boş/geçersiz çıktı veya token sayısı döndürdü")
            for m, p, (metin, token) in zip(malzemeler, promptlar, sonuclar):
                sayac += 1
                kayit = {"surum": KAYIT_SURUMU, "id": f"{tur}-{sayac:07d}", "tur": tur, "malzeme": m.sozluk(), "prompt": p,
                         "cikti": metin, "model": model, "tohum": tohum, "token": token, "saniye": round(sure / n, 3)}
                f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
            f.flush()
            toplam_token += sum(t for _, t in sonuclar)
            toplam_sure += sure
            hiz = (sayac - baslangic) / toplam_sure * 3600
            print(f"{sayac}/{adet} · {toplam_token / toplam_sure:.0f} token/sn · saatte ~{hiz:.0f} {tur}")


def main():
    ap = argparse.ArgumentParser(description="Öğretmen modelle toplu veri üretimi")
    ap.add_argument("--tur", choices=["hikaye", "kart"], required=True)
    ap.add_argument("--adet", type=int, required=True)
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--motor", choices=["auto", "vllm", "transformers"], default="auto")
    ap.add_argument("--grup", type=int, default=64, help="Bir seferde kaç istek (transformers için 8-16 önerilir)")
    ap.add_argument("--tohum", type=int, default=None)
    ap.add_argument("--model", default=OGRETMEN_MODEL)
    a = ap.parse_args()
    uret(a.tur, a.adet, a.cikti, a.motor, a.grup, a.tohum, a.model)


if __name__ == "__main__":
    main()
