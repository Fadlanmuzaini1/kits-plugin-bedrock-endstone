"""
Sub-command KHUSUS ADMIN: create, edit, delete, cooldown, permission.

Semua handler yang butuh akses inventory (`create`, `edit`) memvalidasi
sender adalah `Player` terlebih dahulu -- console tidak punya
inventory. Aturan folder `commands/` tetap berlaku: parsing argumen &
feedback pesan saja, business logic ada di `KitManager`.
"""
from __future__ import annotations

from typing import List, Optional

from endstone import Player
from endstone.command import CommandSender

from endstone_kits.config.config_schema import KitsConfig
from endstone_kits.managers.kit_manager import KitManager


class KitAdminCommands:
    def __init__(self, kit_manager: KitManager, config: KitsConfig):
        self._kit_manager = kit_manager
        self._config = config

    def create(self, sender: CommandSender, args: List[str]) -> None:
        if not self._require_player(sender):
            return
        if len(args) < 2:
            sender.send_message(
                f"{self._config.prefix}Gunakan: "
                f"/kit create <id> <cooldown_detik> [nama tampilan]"
            )
            return

        kit_id = args[0]

        try:
            cooldown_seconds = int(args[1])
        except ValueError:
            sender.send_message(
                f"{self._config.prefix}Cooldown harus berupa angka bulat (detik)."
            )
            return

        display_name = " ".join(args[2:]) if len(args) > 2 else None

        try:
            kit = self._kit_manager.create_from_inventory(
                kit_id, sender.inventory, cooldown_seconds, display_name
            )
        except ValueError as e:
            sender.send_message(f"{self._config.prefix}{e}")
            return

        sender.send_message(
            f"{self._config.prefix}"
            f"{self._config.message('kit_created').format(kit=kit.id)} "
            f"({len(kit.items)} item, cooldown {kit.metadata.cooldown_seconds}s, "
            f"permission '{kit.metadata.permission}')."
        )

    def edit(self, sender: CommandSender, args: List[str]) -> None:
        if not self._require_player(sender):
            return
        if not args:
            sender.send_message(f"{self._config.prefix}Gunakan: /kit edit <id>")
            return

        kit_id = args[0]
        try:
            kit = self._kit_manager.edit_items_from_inventory(
                kit_id, sender.inventory
            )
        except ValueError as e:
            sender.send_message(f"{self._config.prefix}{e}")
            return

        sender.send_message(
            f"{self._config.prefix}Kit '{kit.id}' berhasil diperbarui "
            f"({len(kit.items)} item disimpan)."
        )

    def delete(self, sender: CommandSender, args: List[str]) -> None:
        if not args:
            sender.send_message(f"{self._config.prefix}Gunakan: /kit delete <id>")
            return

        kit_id = args[0]
        if self._kit_manager.delete(kit_id):
            sender.send_message(f"{self._config.prefix}Kit '{kit_id}' berhasil dihapus.")
        else:
            sender.send_message(
                f"{self._config.prefix}"
                f"{self._config.message('kit_not_found').format(kit=kit_id)}"
            )

    def description(self, sender: CommandSender, args: List[str]) -> None:
        if len(args) < 2:
            sender.send_message(
                f"{self._config.prefix}Gunakan: /kit description <id> <teks...>"
            )
            return

        kit_id = args[0]
        text = " ".join(args[1:])

        try:
            kit = self._kit_manager.set_description(kit_id, text)
        except ValueError as e:
            sender.send_message(f"{self._config.prefix}{e}")
            return

        sender.send_message(
            f"{self._config.prefix}Deskripsi kit '{kit.id}' diatur ke: {text}"
        )

    def onetime(self, sender: CommandSender, args: List[str]) -> None:
        if len(args) < 2:
            sender.send_message(
                f"{self._config.prefix}Gunakan: /kit onetime <id> <true|false>"
            )
            return

        kit_id, raw = args[0], args[1].lower()
        if raw not in ("true", "false"):
            sender.send_message(f"{self._config.prefix}Nilai harus 'true' atau 'false'.")
            return

        enabled = raw == "true"
        try:
            kit = self._kit_manager.set_one_time(kit_id, enabled)
        except ValueError as e:
            sender.send_message(f"{self._config.prefix}{e}")
            return

        status = (
            "sekali pakai per player (cooldown diabaikan)"
            if enabled
            else "bisa diklaim berulang mengikuti cooldown"
        )
        sender.send_message(f"{self._config.prefix}Kit '{kit.id}' sekarang {status}.")

    def cooldown(self, sender: CommandSender, args: List[str]) -> None:
        if len(args) < 2:
            sender.send_message(
                f"{self._config.prefix}Gunakan: /kit cooldown <id> <detik>"
            )
            return

        kit_id, raw_seconds = args[0], args[1]
        try:
            seconds = int(raw_seconds)
        except ValueError:
            sender.send_message(f"{self._config.prefix}Detik harus berupa angka bulat.")
            return

        try:
            kit = self._kit_manager.set_cooldown(kit_id, seconds)
        except ValueError as e:
            sender.send_message(f"{self._config.prefix}{e}")
            return

        sender.send_message(
            f"{self._config.prefix}Cooldown kit '{kit.id}' diatur ke "
            f"{kit.metadata.cooldown_seconds} detik."
        )

    def permission(self, sender: CommandSender, args: List[str]) -> None:
        if not args:
            sender.send_message(
                f"{self._config.prefix}Gunakan: /kit permission <id> <node|none>"
            )
            return

        kit_id = args[0]
        node: Optional[str] = args[1] if len(args) > 1 else None
        if node and node.lower() == "none":
            node = None

        try:
            kit = self._kit_manager.set_permission(kit_id, node)
        except ValueError as e:
            sender.send_message(f"{self._config.prefix}{e}")
            return

        sender.send_message(
            f"{self._config.prefix}Permission kit '{kit.id}' diatur ke "
            f"{kit.metadata.permission or '(tidak ada)'}."
        )

    def addcommand(self, sender: CommandSender, args: List[str]) -> None:
        # Sengaja TIDAK memakai `_require_player` -- addcommand tidak
        # butuh inventory, jadi boleh dijalankan dari console juga.
        if len(args) < 3:
            sender.send_message(
                f"{self._config.prefix}Gunakan: "
                f"/kit addcommand <id> <player|console> <command...>"
            )
            return

        kit_id = args[0]
        run_as = args[1].lower()
        if run_as not in ("player", "console"):
            sender.send_message(
                f"{self._config.prefix}Tipe eksekusi harus 'player' atau 'console'."
            )
            return

        template = " ".join(args[2:])

        try:
            kit = self._kit_manager.add_command(kit_id, template, run_as=run_as)
        except ValueError as e:
            sender.send_message(f"{self._config.prefix}{e}")
            return

        sender.send_message(
            f"{self._config.prefix}Command '{template}' ({run_as}) ditambahkan "
            f"ke kit '{kit.id}' (total {len(kit.commands)} command)."
        )

    def removecommand(self, sender: CommandSender, args: List[str]) -> None:
        if len(args) < 2:
            sender.send_message(
                f"{self._config.prefix}Gunakan: /kit removecommand <id> <index>"
            )
            return

        kit_id, raw_index = args[0], args[1]
        try:
            # Input user 1-based (lebih ramah admin, sesuai penomoran
            # yang ditampilkan `/kit info`) -> dikonversi ke 0-based
            # sebelum diteruskan ke KitManager.
            index = int(raw_index) - 1
        except ValueError:
            sender.send_message(f"{self._config.prefix}Index harus berupa angka bulat.")
            return

        try:
            kit = self._kit_manager.remove_command(kit_id, index)
        except ValueError as e:
            sender.send_message(f"{self._config.prefix}{e}")
            return

        sender.send_message(
            f"{self._config.prefix}Command ke-{raw_index} dihapus dari kit "
            f"'{kit.id}' (sisa {len(kit.commands)} command)."
        )

    # ------------------------------------------------------------------
    def _require_player(self, sender: CommandSender) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(
                f"{self._config.prefix}Perintah ini hanya bisa dijalankan "
                f"oleh player (butuh akses inventory), bukan console."
            )
            return False
        return True
