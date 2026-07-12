"""Format durasi detik menjadi teks yang mudah dibaca, dipakai untuk
menampilkan sisa waktu cooldown ke player."""
from __future__ import annotations


def format_duration(seconds: int, style: str = "long") -> str:
    """
    style="long"  -> "1 hari 2 jam 3 menit 4 detik"
    style="short" -> "1h 2j 3m 4d"

    Bagian bernilai 0 di AWAL dilewati (mis. "5 menit 2 detik", bukan
    "0 hari 0 jam 5 menit 2 detik"), tapi unit terakhir tetap
    ditampilkan walau 0 (mis. "0 detik") supaya hasilnya tidak pernah
    berupa string kosong.
    """
    seconds = max(0, int(seconds))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    if style == "short":
        labels = ["h", "j", "m", "d"]
    else:
        labels = ["hari", "jam", "menit", "detik"]

    values = [days, hours, minutes, secs]

    result = []
    started = False
    for i, (value, label) in enumerate(zip(values, labels)):
        is_last = i == len(values) - 1
        if value == 0 and not started and not is_last:
            continue
        started = True
        if style == "short":
            result.append(f"{value}{label}")
        else:
            result.append(f"{value} {label}")

    return " ".join(result)
