"""
Event handler untuk lazy-load cache cooldown saat player join, dan
membuangnya saat player quit. Lihat dokumen desain §6.2 dan
`managers/cooldown_manager.py`.

CATATAN: file ini SENGAJA TIDAK memakai
`from __future__ import annotations`. Mekanisme `register_events()`
Endstone membaca type hint parameter method (`event: PlayerJoinEvent`)
untuk menentukan event apa yang didaftarkan, dan pembacaan ini butuh
objek class asli saat runtime -- bukan string. `from __future__ import
annotations` membuat semua annotation jadi string (evaluasi malas),
yang menyebabkan Endstone menolak handler dengan pesan
"invalid event handler signature". Modul lain di proyek ini aman
memakainya karena tidak diregistrasi lewat mekanisme reflection ini.
"""

from endstone.event import PlayerJoinEvent, PlayerQuitEvent, event_handler

from endstone_kits.managers.cooldown_manager import CooldownManager


class PlayerListener:
    def __init__(self, cooldown_manager: CooldownManager):
        self._cooldown_manager = cooldown_manager

    @event_handler
    def on_player_join(self, event: PlayerJoinEvent):
        self._cooldown_manager.load_player(str(event.player.unique_id))

    @event_handler
    def on_player_quit(self, event: PlayerQuitEvent):
        self._cooldown_manager.unload_player(str(event.player.unique_id))
