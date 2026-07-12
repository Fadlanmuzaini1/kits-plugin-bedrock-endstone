"""
Utility warna/format teks Bedrock.

Bedrock memakai simbol section (§) untuk kode warna/format (mis. §b =
aqua, §c = merah) -- BUKAN "&" seperti konvensi umum plugin ala Bukkit.
`endstone.ColorFormat` menyediakan konstanta § siap pakai untuk dipakai
langsung di kode Python (mis. `ColorFormat.YELLOW`), tapi untuk teks
yang disimpan di file config.toml, karakter § kadang bermasalah untuk
diketik/disimpan di beberapa editor teks & encoding (terutama Windows).

Solusinya: admin tetap menulis "&" di config.toml (familiar & aman
diketik), lalu di-translate ke "§" oleh fungsi ini sebelum pesan
dikirim ke player. Ini satu-satunya tempat translasi terjadi --
`KitsConfig` memanggil fungsi ini, jadi kode lain (command, manager)
tidak perlu tahu detail ini sama sekali.
"""
from __future__ import annotations

# Karakter kode warna/format yang valid di Bedrock (0-9, a-f untuk
# warna; k-o & r untuk format seperti bold/italic/reset).
_VALID_CODES = "0123456789abcdefklmnor"


def translate_color_codes(text: str, alt_color_char: str = "&") -> str:
    """Ganti "&<kode>" menjadi "§<kode>" untuk kode yang valid.

    Kombinasi yang tidak dikenal (mis. "&x", atau "&" di akhir string)
    dibiarkan apa adanya, supaya teks yang kebetulan mengandung "&"
    biasa (bukan kode warna) tidak ikut ter-translate secara keliru.
    """
    if not text:
        return text

    result: list[str] = []
    i = 0
    length = len(text)
    while i < length:
        char = text[i]
        if (
            char == alt_color_char
            and i + 1 < length
            and text[i + 1].lower() in _VALID_CODES
        ):
            result.append("\u00a7")
            result.append(text[i + 1].lower())
            i += 2
        else:
            result.append(char)
            i += 1
    return "".join(result)
