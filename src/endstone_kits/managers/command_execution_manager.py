"""
CommandExecutionManager: satu-satunya business logic untuk menjalankan
command isi kit saat diklaim.
"""
from __future__ import annotations

from typing import List, Optional

from endstone_kits.services.placeholder_service import render_placeholders


class CommandExecutionManager:
    def __init__(self, server=None):
        # `server` HANYA dibutuhkan untuk command dengan run_as="console"
        # (lewat `server.dispatch_command(server.command_sender, ...)`).
        # Dibuat opsional (default None) supaya class ini tetap mudah
        # diuji tanpa objek server sungguhan untuk kasus run_as="player"
        # saja.
        self._server = server

    def execute_all(self, player, commands: List, logger=None) -> None:
        """Jalankan seluruh command isi kit satu per satu.

        Satu command yang gagal (mis. command tidak dikenal, atau
        `perform_command`/`dispatch_command` melempar exception) TIDAK
        menghentikan command berikutnya -- konsisten dengan prinsip
        yang sama seperti enchant tidak valid di `ItemSerializer`
        (Tahap 2): satu bagian kit yang bermasalah tidak boleh
        menggagalkan seluruh proses klaim.
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

        if entry.run_as == "player":
            # Dieksekusi DENGAN permission player itu sendiri (bukan
            # operator) -- dikonfirmasi dari changelog Endstone soal
            # `Player.perform_command`.
            player.perform_command(rendered)
        elif entry.run_as == "console":
            # Dieksekusi sebagai server/console -- permission penuh,
            # cocok untuk command yang butuh hak admin (mis. `give`,
            # `gamemode` ke player lain, dll) tanpa player perlu punya
            # izin itu sendiri.
            if self._server is None:
                raise RuntimeError(
                    "CommandExecutionManager tidak punya referensi "
                    "server -- tidak bisa menjalankan command sebagai "
                    "console."
                )
            self._server.dispatch_command(self._server.command_sender, rendered)
        # `run_as` selain "player"/"console" (tidak seharusnya terjadi
        # lewat command normal, tapi bisa muncul dari kits.json yang
        # diedit manual) sengaja diabaikan secara diam-diam, bukan
        # error -- titik ekstensi untuk opsi run_as lain di masa depan.
