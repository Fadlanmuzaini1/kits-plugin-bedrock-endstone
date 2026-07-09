"""
Sub-command untuk PLAYER biasa (bukan admin): list, info, claim.

Aturan folder `commands/`: hanya parsing argumen & feedback pesan,
TIDAK ada business logic -- semua logic ada di `KitManager` /
`CooldownManager`.
"""
from __future__ import annotations

from typing import List

from endstone import Player
from endstone.command import CommandSender

from endstone_kits.config.config_schema import KitsConfig
from endstone_kits.managers.command_execution_manager import CommandExecutionManager
from endstone_kits.managers.cooldown_manager import CooldownManager
from endstone_kits.managers.kit_manager import KitManager
from endstone_kits.managers.permission_manager import PermissionManager
from endstone_kits.utils.time_format import format_duration


class KitPlayerCommands:
    def __init__(
        self,
        kit_manager: KitManager,
        cooldown_manager: CooldownManager,
        permission_manager: PermissionManager,
        command_execution_manager: CommandExecutionManager,
        config: KitsConfig,
        logger=None,
    ):
        self._kit_manager = kit_manager
        self._cooldown_manager = cooldown_manager
        self._permission_manager = permission_manager
        self._command_execution_manager = command_execution_manager
        self._config = config
        self._logger = logger

    def list_kits(self, sender: CommandSender) -> None:
        all_kits = self._kit_manager.list_all()
        # Filter kit berdasarkan permission -- sejak Tahap 4, hanya
        # kit yang boleh diakses sender yang ditampilkan (kit dengan
        # `permission=None` selalu terlihat oleh siapa pun).
        kits = [k for k in all_kits if self._permission_manager.can_access(sender, k)]

        if not kits:
            sender.send_message(f"{self._config.prefix}Belum ada kit yang bisa kamu akses.")
            return

        lines = [f"{self._config.prefix}Daftar kit ({len(kits)}):"]
        for kit in kits:
            lines.append(
                f"  - {kit.id} ({kit.metadata.display_name}): "
                f"{len(kit.items)} item, cooldown {kit.metadata.cooldown_seconds}s"
            )
        sender.send_message("\n".join(lines))

    def info(self, sender: CommandSender, kit_id: str) -> None:
        """Info kit tetap ditampilkan ke siapa pun dengan `kits.use`,
        TIDAK digate oleh permission kit spesifik (beda dengan `list`
        & `claim`) -- supaya player tahu syarat permission apa yang
        perlu diminta ke staff untuk kit yang diinginkan, tanpa perlu
        staff membocorkannya secara manual."""
        kit = self._kit_manager.get(kit_id)
        if kit is None:
            sender.send_message(
                f"{self._config.prefix}"
                f"{self._config.message('kit_not_found').format(kit=kit_id)}"
            )
            return

        meta = kit.metadata
        lines = [
            f"{self._config.prefix}Info kit '{kit.id}':",
            f"  Nama       : {meta.display_name}",
            f"  Deskripsi  : {meta.description or '-'}",
            f"  Permission : {meta.permission or '(tidak ada)'}",
            f"  Cooldown   : {meta.cooldown_seconds} detik",
            f"  Jumlah item: {len(kit.items)}",
            f"  Jumlah cmd : {len(kit.commands)}",
        ]
        if kit.commands:
            lines.append("  Command:")
            for i, cmd in enumerate(kit.commands, start=1):
                lines.append(f"    {i}. {cmd.template}")
        sender.send_message("\n".join(lines))

    def claim(self, sender: CommandSender, args: List[str]) -> None:
        if not isinstance(sender, Player):
            sender.send_message(
                f"{self._config.prefix}Perintah ini hanya bisa dijalankan "
                f"oleh player, bukan console."
            )
            return
        if not args:
            sender.send_message(f"{self._config.prefix}Gunakan: /kit claim <id>")
            return

        self.claim_kit(sender, args[0])

    def claim_kit(self, sender, kit_id: str) -> None:
        """Logic klaim sesungguhnya, DIPISAH dari `claim()` (yang
        cuma parsing argumen command teks) supaya bisa dipanggil
        langsung dari tombol GUI (`managers/gui_manager.py`) tanpa
        duplikasi logic bisnis -- lihat dokumen desain §2 prinsip #1.
        `sender` di sini sudah pasti instance `Player` (dijamin oleh
        pemanggil: `claim()` sudah mengecek, GUI hanya bisa dibuka
        oleh Player)."""
        kit = self._kit_manager.get(kit_id)
        if kit is None:
            sender.send_message(
                f"{self._config.prefix}"
                f"{self._config.message('kit_not_found').format(kit=kit_id)}"
            )
            return

        # NOTE (sejak Tahap 4): pengecekan permission per-kit lewat
        # PermissionManager. Kit dengan `permission=None` bisa
        # diklaim siapa saja yang punya izin dasar `kits.use`.
        if not self._permission_manager.can_access(sender, kit):
            sender.send_message(
                f"{self._config.prefix}{self._config.message('no_permission')}"
            )
            return

        player_uuid = str(sender.unique_id)

        remaining = self._cooldown_manager.get_remaining_seconds(
            player_uuid, kit.id, kit.metadata.cooldown_seconds
        )
        if remaining > 0:
            time_text = format_duration(remaining, self._config.cooldown_time_format)
            sender.send_message(
                f"{self._config.prefix}"
                f"{self._config.message('cooldown_active').format(time=time_text)}"
            )
            return

        # Reserve-then-commit (lihat dokumen desain §6.3): cegah
        # dobel klaim dari double-klik GUI/command sebelum proses
        # pemberian item sebelumnya selesai.
        if not self._cooldown_manager.try_reserve(player_uuid, kit.id):
            sender.send_message(
                f"{self._config.prefix}{self._config.message('claim_in_progress')}"
            )
            return

        try:
            leftover = self._kit_manager.grant_items_to(kit.id, sender)
            # Command isi kit dijalankan SETELAH item diberikan, masih
            # di dalam blok try yang sama -- kalau command melempar
            # exception, cooldown TETAP tidak dicatat (opsi B di
            # dokumen desain §6.3), tapi item yang sudah terlanjur
            # diberikan tidak ditarik kembali (rollback item bukan hal
            # sepele di Bedrock, dan requirement tidak memintanya).
            # `execute_all` sendiri sudah menahan exception PER
            # command supaya satu command salah tidak menghentikan
            # command lain dalam kit yang sama.
            self._command_execution_manager.execute_all(
                sender, kit.commands, logger=self._logger
            )
        finally:
            self._cooldown_manager.release(player_uuid, kit.id)

        # Cooldown dicatat SETELAH proses grant selesai sukses (opsi B
        # di dokumen desain §6.3) -- kalau grant di atas melempar
        # exception, baris ini tidak akan tereksekusi sehingga player
        # tidak dikenai cooldown untuk kit yang gagal diberikan.
        self._cooldown_manager.mark_claimed(player_uuid, kit.id)

        sender.send_message(
            f"{self._config.prefix}"
            f"{self._config.message('kit_claimed').format(kit=kit.id)}"
        )
        if leftover:
            sender.send_message(
                f"{self._config.prefix}"
                f"{self._config.message('inventory_full').format(count=len(leftover))}"
            )
