from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KitCommandEntry:
    """Satu baris command yang dijalankan saat kit diklaim.

    `run_as` sengaja dibuat string (bukan hardcode "player") supaya
    kalau suatu saat dibutuhkan opsi "console", field ini tinggal
    diberi nilai baru tanpa mengubah struktur data. Requirement saat
    ini mewajibkan command dijalankan sebagai player -- lihat
    `services/placeholder_service.py` & `managers/command_execution_manager.py`
    di Tahap 5.
    """

    template: str  # mis. "give {player} diamond 1"
    run_as: str = "player"

    def to_dict(self) -> dict:
        return {"template": self.template, "run_as": self.run_as}

    @staticmethod
    def from_dict(data: dict) -> "KitCommandEntry":
        return KitCommandEntry(
            template=data["template"], run_as=data.get("run_as", "player")
        )
