"""
Event handler untuk event Endstone (mis. PlayerJoinEvent, PlayerQuitEvent).

Dipakai antara lain untuk lazy-load cooldown player ke cache saat join,
dan membuang cache tersebut saat player quit (lihat CooldownManager di
Tahap 3).

PENTING -- berlaku untuk SEMUA file listener di folder ini: JANGAN
memakai `from __future__ import annotations` di file yang berisi
method `@event_handler`. Endstone membaca annotation parameter event
lewat `inspect.isclass(...)` saat `register_events()` dipanggil, yang
mengharuskan annotation berupa objek class asli saat runtime -- bukan
string. `from __future__ import annotations` membuat semua annotation
jadi string (evaluasi malas) dan menyebabkan Endstone menolak handler
dengan pesan "invalid event handler signature".
"""
