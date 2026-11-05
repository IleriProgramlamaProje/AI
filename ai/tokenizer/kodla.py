"""Belgeleri token numaralarına çevirir (O1'in tokenizer bağlantısı). hazirla.py bunu çağırır.

    from ai.tokenizer.kodla import kodla
    kodla("ai/tokenizer/cikti/tokenizer.json", belge_listesi, "train.bin")

Çıktı: art arda yazılmış uint16 token numaraları, her belgenin sonunda <|son|>.
"""
import numpy as np
from tokenizers import Tokenizer

from ai.tokenizer.egit_tokenizer import SON


def kodla(tokenizer_yolu, belgeler, cikti, grup=1000):
    """Belgeleri `cikti`ya yazar, toplam token sayısını döndürür."""
    tok = Tokenizer.from_file(str(tokenizer_yolu))
    if tok.get_vocab_size() > 65536:
        raise ValueError("uint16'ya sığmıyor: kelime dağarcığı 65536'dan büyük")
    son = tok.token_to_id(SON)
    toplam = 0
    with open(cikti, "wb") as f:
        for i in range(0, len(belgeler), grup):
            for k in tok.encode_batch(belgeler[i:i + grup]):
                dizi = np.array(k.ids + [son], dtype=np.uint16)
                dizi.tofile(f)
                toplam += len(dizi)
    return toplam
