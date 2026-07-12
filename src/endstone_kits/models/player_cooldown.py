from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlayerCooldown:
    """Representasi satu baris cooldown (player + kit + waktu klaim
    terakhir), mencerminkan 1 baris di tabel `cooldowns` SQLite.

    `CooldownManager` sendiri memakai dict sederhana `(uuid, kit_id) ->
    epoch` sebagai cache in-memory demi performa (lihat dokumen desain
    §6.2) -- model ini terutama berguna untuk testing/debugging dan
    kejelasan dokumentasi struktur data.
    """

    player_uuid: str
    kit_id: str
    last_claimed_at: int  # epoch detik

    def to_dict(self) -> dict:
        return {
            "player_uuid": self.player_uuid,
            "kit_id": self.kit_id,
            "last_claimed_at": self.last_claimed_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "PlayerCooldown":
        return PlayerCooldown(
            player_uuid=data["player_uuid"],
            kit_id=data["kit_id"],
            last_claimed_at=data["last_claimed_at"],
        )
