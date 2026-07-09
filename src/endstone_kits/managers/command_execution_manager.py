"""
CommandExecutionManager: satu-satunya business logic untuk menjalankan
command isi kit saat diklaim.
"""
from __future__ import annotations

from typing import List, Optional

from endstone_kits.services.placeholder_service import render_placeholders


class CommandExecutionManager:
    def execute_all(self, player, commands: List, logger=None) -> None:
        """Jalankan seluruh command isi kit satu per satu.

        Satu command yang gagal (mis. command tidak dikenal, atau
        `perform_command` melempar exception) TIDAK menghentikan
        command berikutnya -- konsisten dengan prinsip yang sama
        seperti enchant tidak valid di `ItemSerializer` (Tahap 2):
        satu bagian kit yang bermasalah tidak boleh menggagalkan
        seluruh proses klaim.
        """
        for entry in commands:
            try:
                self.execute_one(player, entry)
            except Exception as e:  # noqa: BLE001 -- lihat docstring
                if logger is not None:
                    logger.warning(
                        f"Kits: gagal menjalankan command kit "
                        f"'{entry.template}' untuk {player.name}: {e}"
                    )

    def execute_one(self, player, entry) -> None:
        rendered = render_placeholders(entry.template, player)
        # `run_as` saat ini hanya mendukung "player" sesuai requirement
        # utama (command dieksekusi dengan permission player itu
        # sendiri, BUKAN console/operator). Field ini disiapkan sebagai
        # titik ekstensi di `models/kit_command_entry.py` untuk opsi
        # lain di masa depan tanpa mengubah struktur data.
        if entry.run_as == "player":
            player.perform_command(rendered)
