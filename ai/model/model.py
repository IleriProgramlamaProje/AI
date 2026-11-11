"""Küçük GPT modeli (görev 3.2). nanoGPT (Karpathy, MIT) örnek alınarak sadeleştirildi.

Model metni token token yazar: her adımda o ana kadarki token'lara bakıp bir sonraki token'ın
olasılıklarını verir. Eğitimde bu tahmin, gerçek bir sonraki token'la karşılaştırılır (kayıp).

Parçalar (yukarıdan aşağı):
  1. Gömme (tok_gom): her token numarasını `genislik` uzunluğunda bir sayı listesine çevirir.
  2. Konum gömmesi (konum_gom): token'ın cümlede kaçıncı sırada olduğunu ekler.
  3. `katman` tane Blok: her blokta
       - Dikkat (Dikkat): her token, kendinden önceki token'lara bakıp hangisinin önemli olduğunu seçer.
         `kafa` tane paralel dikkat vardır; her biri farklı bir ilişkiye bakabilir (özne-yüklem, etiket-sayı…).
       - İleri besleme (MLP): her token'ın bilgisini tek başına işler.
     Her iki kısımdan önce LayerNorm (sayıları ölçekler), sonra artık bağlantı (x = x + ...) vardır.
  4. Son LayerNorm ve çıkış (cikis): her token için sözlükteki 8000 parçanın her birine bir puan.
     Çıkış ağırlıkları gömmeyle ortaktır (weight tying): parametre tasarrufu, küçük modelde önemli.

Boyutlar ai/model/boyutlar/*.yaml dosyalarında.
"""
import math
from dataclasses import dataclass, fields

import torch
import torch.nn as nn
from torch.nn import functional as F


@dataclass
class Ayar:
    sozluk: int = 8000       # tokenizer'ın kelime dağarcığı (token sayısı)
    baglam: int = 256        # modelin aynı anda görebildiği en fazla token
    katman: int = 4          # blok sayısı (derinlik)
    kafa: int = 4            # dikkat kafası sayısı; genislik / kafa tam bölünmeli
    genislik: int = 128      # her token'ı temsil eden sayı listesinin uzunluğu
    dropout: float = 0.0     # eğitimde rastgele söndürme oranı (ezberi azaltır)

    @classmethod
    def sozlukten(cls, d):
        """yaml/sözlükten Ayar; bilinmeyen anahtarlar (eğitim ayarları gibi) atlanır."""
        adlar = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in adlar})


class Dikkat(nn.Module):
    """Nedensel öz-dikkat: her token yalnızca kendinden ÖNCEKİ token'lara bakar (geleceği göremez)."""

    def __init__(self, a: Ayar):
        super().__init__()
        assert a.genislik % a.kafa == 0, "genislik kafa sayısına tam bölünmeli"
        self.kafa, self.dropout = a.kafa, a.dropout
        self.qkv = nn.Linear(a.genislik, 3 * a.genislik, bias=False)   # sorgu, anahtar, değer tek seferde
        self.proj = nn.Linear(a.genislik, a.genislik, bias=False)
        self.son_drop = nn.Dropout(a.dropout)

    def forward(self, x):
        B, T, C = x.shape                                                 # yığın, uzunluk, genişlik
        q, k, v = self.qkv(x).split(C, dim=2)
        # (B, T, C) -> (B, kafa, T, C/kafa): her kafa kendi alt uzayında çalışır
        q, k, v = (t.view(B, T, self.kafa, C // self.kafa).transpose(1, 2) for t in (q, k, v))
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True,
                                           dropout_p=self.dropout if self.training else 0.0)
        y = y.transpose(1, 2).contiguous().view(B, T, C)                 # kafaları birleştir
        return self.son_drop(self.proj(y))


class MLP(nn.Module):
    """İleri besleme: genişliği 4 katına açıp GELU'dan geçirir, geri daraltır."""

    def __init__(self, a: Ayar):
        super().__init__()
        self.ac = nn.Linear(a.genislik, 4 * a.genislik, bias=False)
        self.kapa = nn.Linear(4 * a.genislik, a.genislik, bias=False)
        self.drop = nn.Dropout(a.dropout)

    def forward(self, x):
        return self.drop(self.kapa(F.gelu(self.ac(x))))


class Blok(nn.Module):
    def __init__(self, a: Ayar):
        super().__init__()
        self.ln1, self.dikkat = nn.LayerNorm(a.genislik), Dikkat(a)
        self.ln2, self.mlp = nn.LayerNorm(a.genislik), MLP(a)

    def forward(self, x):
        x = x + self.dikkat(self.ln1(x))     # artık bağlantı: öğrenilen şey eskisinin ÜSTÜNE eklenir
        x = x + self.mlp(self.ln2(x))
        return x


class GPT(nn.Module):
    def __init__(self, a: Ayar):
        super().__init__()
        self.ayar = a
        self.tok_gom = nn.Embedding(a.sozluk, a.genislik)
        self.konum_gom = nn.Embedding(a.baglam, a.genislik)
        self.drop = nn.Dropout(a.dropout)
        self.bloklar = nn.ModuleList(Blok(a) for _ in range(a.katman))
        self.ln_son = nn.LayerNorm(a.genislik)
        self.cikis = nn.Linear(a.genislik, a.sozluk, bias=False)
        self.cikis.weight = self.tok_gom.weight      # weight tying
        self.apply(self._baslat)
        # GPT-2: artık bağlantıya eklenen katmanlar derinliğe göre daha küçük başlatılır
        for ad, p in self.named_parameters():
            if ad.endswith("proj.weight") or ad.endswith("kapa.weight"):
                nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * a.katman))

    @staticmethod
    def _baslat(m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)

    def parametre_sayisi(self, konum_haric=False):
        """Toplam parametre (ortak gömme bir kez sayılır)."""
        n = sum(p.numel() for p in self.parameters())
        return n - self.konum_gom.weight.numel() if konum_haric else n

    def forward(self, idx, hedef=None):
        """idx: (B, T) token numaraları. hedef verilirse (B, T) bir sonraki token'lar; kayıp döner."""
        B, T = idx.shape
        assert T <= self.ayar.baglam, f"dizi {T} token, bağlam en fazla {self.ayar.baglam}"
        konum = torch.arange(T, device=idx.device)
        x = self.drop(self.tok_gom(idx) + self.konum_gom(konum))
        for blok in self.bloklar:
            x = blok(x)
        x = self.ln_son(x)
        if hedef is None:
            return self.cikis(x[:, [-1], :]), None          # üretimde sadece son konumun puanları gerekir
        logits = self.cikis(x)
        kayip = F.cross_entropy(logits.view(-1, logits.size(-1)), hedef.view(-1))
        return logits, kayip

    @torch.no_grad()
    def uret(self, idx, max_yeni, sicaklik=0.8, top_k=None, dur=None):
        """idx'in devamını token token üretir.

        sicaklik: düşük = güvenli ve tekdüze, yüksek = çeşitli ama hataya açık (oyunda 0,7–0,9 denenecek).
        top_k   : her adımda yalnızca en olası k token arasından seçer (saçma token'ları keser).
        dur     : bu token üretilince durur (ör. <|son|> ya da </kart>).
        """
        self.eval()
        for _ in range(max_yeni):
            girdi = idx[:, -self.ayar.baglam:]                 # bağlamdan uzunsa sadece son kısım
            logits, _ = self(girdi)
            logits = logits[:, -1, :] / max(sicaklik, 1e-5)
            if top_k:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = -float("inf")
            sonraki = torch.multinomial(F.softmax(logits, dim=-1), num_samples=1)
            idx = torch.cat((idx, sonraki), dim=1)
            if dur is not None and (sonraki == dur).all():
                break
        return idx
