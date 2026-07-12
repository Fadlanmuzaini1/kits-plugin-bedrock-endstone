"""
CooldownManager: satu-satunya business logic untuk cooldown klaim kit.

Bergantung HANYA pada interface `CooldownRepository` (bukan implementasi
SQLite konkret), sama seperti `KitManager` -- lihat dokumen desain §2
prinsip #2.
"""
from __future__ import annotations

import time
from typing import Dict, Set, Tuple

from endstone_kits.storage.base import CooldownRepository


class CooldownManager:
    def __init__(self, repository: CooldownRepository):
        self._repository = repository

        # Cache in-memory: (player_uuid, kit_id) -> last_claimed_at
        # (epoch detik). DI-LAZY-LOAD per player saat join (bukan
        # semua player sekaligus saat startup) dan DIBUANG saat quit
        # -- supaya memory tidak membengkak di server dengan banyak
        # player & banyak kit dalam jangka panjang. Lihat dokumen
        # desain §6.2.
        self._cache: Dict[Tuple[str, str], int] = {}

        # Player yang datanya sudah pernah di-load ke cache -- dipakai
        # supaya `load_player` idempotent (tidak query database
        # berulang kalau dipanggil lebih dari sekali untuk player yang
        # sama).
        self._loaded_players: Set[str] = set()

        # Lock in-memory: kombinasi (player, kit) yang SEDANG diproses
        # klaimnya. Mencegah double-klaim dari GUI/command yang
        # dipencet berkali-kali sangat cepat sebelum proses pertama
        # selesai -- lihat pola "reserve-then-commit" di dokumen
        # desain §6.3.
        self._in_progress: Set[Tuple[str, str]] = set()

    # ------------------------------------------------------------------
    # Lifecycle per player (dipanggil dari listeners/player_listener.py)
    # ------------------------------------------------------------------
    def load_player(self, player_uuid: str) -> None:
        """Lazy-load seluruh cooldown milik 1 player ke cache saat dia
        join server."""
        if player_uuid in self._loaded_players:
            return
        for kit_id, last_claimed_at in self._repository.get_all_for_player(
            player_uuid
        ).items():
            self._cache[(player_uuid, kit_id)] = last_claimed_at
        self._loaded_players.add(player_uuid)

    def unload_player(self, player_uuid: str) -> None:
        """Buang seluruh entri cache milik 1 player saat dia quit."""
        keys_to_remove = [key for key in self._cache if key[0] == player_uuid]
        for key in keys_to_remove:
            del self._cache[key]
        self._loaded_players.discard(player_uuid)
        self._in_progress = {
            key for key in self._in_progress if key[0] != player_uuid
        }

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def get_remaining_seconds(
        self, player_uuid: str, kit_id: str, cooldown_seconds: int
    ) -> int:
        """Sisa waktu cooldown dalam detik. 0 berarti sudah boleh klaim."""
        if cooldown_seconds <= 0:
            return 0
        last_claimed_at = self._cache.get((player_uuid, kit_id))
        if last_claimed_at is None:
            return 0
        elapsed = int(time.time()) - last_claimed_at
        remaining = cooldown_seconds - elapsed
        return max(0, remaining)

    def can_claim(self, player_uuid: str, kit_id: str, cooldown_seconds: int) -> bool:
        return self.get_remaining_seconds(player_uuid, kit_id, cooldown_seconds) == 0

    def has_ever_claimed(self, player_uuid: str, kit_id: str) -> bool:
        """Untuk kit ONE-TIME: cek apakah player PERNAH klaim kit ini
        kapan pun, TANPA peduli sudah berapa lama berlalu -- beda dari
        `get_remaining_seconds`/`can_claim` yang menghitung berdasarkan
        `cooldown_seconds` waktu.

        Sengaja memakai ULANG cache & storage cooldown yang sama
        (bukan tabel/field terpisah) -- kalau sebuah baris
        `(player_uuid, kit_id)` pernah tercatat sama sekali, itu berarti
        pernah diklaim. Ini menghindari duplikasi skema penyimpanan
        untuk konsep yang sebenarnya sama (\"kapan terakhir diklaim\"),
        hanya beda cara kit tsb MENAFSIRKAN nilai itu (waktu vs
        keberadaan)."""
        return (player_uuid, kit_id) in self._cache

    # ------------------------------------------------------------------
    # Reserve-then-commit (lihat dokumen desain §6.3)
    # ------------------------------------------------------------------
    def try_reserve(self, player_uuid: str, kit_id: str) -> bool:
        """Tandai (player, kit) sebagai 'sedang diproses'.

        Return False kalau sudah ada proses klaim lain yang berjalan
        untuk kombinasi yang sama persis (mis. double-klik GUI sangat
        cepat). Pemanggil WAJIB memanggil `release()` di blok
        `finally`, supaya lock tidak pernah tersangkut permanen kalau
        terjadi exception di tengah proses pemberian kit.
        """
        key = (player_uuid, kit_id)
        if key in self._in_progress:
            return False
        self._in_progress.add(key)
        return True

    def release(self, player_uuid: str, kit_id: str) -> None:
        self._in_progress.discard((player_uuid, kit_id))

    def mark_claimed(self, player_uuid: str, kit_id: str) -> None:
        """Catat waktu klaim SEKARANG untuk kombinasi player+kit.

        Dipanggil setelah seluruh proses grant (pemberian item, dan
        nanti command di Tahap 5) selesai SUKSES -- ini adalah opsi
        (B) "cooldown dicatat sesudah grant selesai" dari dokumen
        desain §6.3, dikombinasikan dengan lock `try_reserve` supaya
        tidak ada celah dobel klaim.
        """
        now = int(time.time())
        self._cache[(player_uuid, kit_id)] = now
        self._repository.upsert(player_uuid, kit_id, now)
        # Pastikan player ini tercatat sebagai "loaded" supaya kalau
        # nanti quit, entri barunya ikut dibersihkan dengan benar oleh
        # `unload_player`.
        self._loaded_players.add(player_uuid)
