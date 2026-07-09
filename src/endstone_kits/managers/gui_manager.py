"""
GUIManager: mengatur KAPAN form dibuka dan data APA yang ditampilkan
di dalamnya. Bentuk visual (ActionForm/tombol) didelegasikan ke
`gui/kit_list_form.py` & `gui/kit_detail_form.py`.

PENTING: logic klaim TIDAK diduplikasi di sini. Tombol "Klaim" di form
detail memanggil langsung `KitPlayerCommands.claim_kit()` -- method
yang sama persis dipakai oleh `/kit claim <id>` versi teks. Ini
memastikan perilaku GUI & command teks selalu identik (permission,
cooldown, reserve-lock, eksekusi command isi kit -- semuanya konsisten
tanpa perlu disinkronkan manual di 2 tempat).
"""
from __future__ import annotations

from endstone_kits.gui.kit_detail_form import build_kit_detail_form
from endstone_kits.gui.kit_list_form import build_kit_list_form
from endstone_kits.utils.time_format import format_duration


class GUIManager:
    def __init__(
        self,
        kit_manager,
        cooldown_manager,
        permission_manager,
        player_commands,
        config,
    ):
        self._kit_manager = kit_manager
        self._cooldown_manager = cooldown_manager
        self._permission_manager = permission_manager
        self._player_commands = player_commands
        self._config = config

    def open_kit_list(self, player) -> None:
        all_kits = self._kit_manager.list_all()
        accessible = [
            kit for kit in all_kits if self._permission_manager.can_access(player, kit)
        ]

        player_uuid = str(player.unique_id)
        entries = [
            (kit, self._status_text(player_uuid, kit)) for kit in accessible
        ]

        form = build_kit_list_form(
            entries,
            title=self._config.gui_title,
            on_select=self.open_kit_detail,
        )
        player.send_form(form)

    def open_kit_detail(self, player, kit_id: str) -> None:
        kit = self._kit_manager.get(kit_id)
        if kit is None:
            player.send_message(
                f"{self._config.prefix}"
                f"{self._config.message('kit_not_found').format(kit=kit_id)}"
            )
            return

        player_uuid = str(player.unique_id)
        status_text = self._status_text(player_uuid, kit)

        form = build_kit_detail_form(
            kit,
            status_text,
            on_claim=lambda p: self._player_commands.claim_kit(p, kit.id),
            on_back=lambda p: self.open_kit_list(p),
        )
        player.send_form(form)

    def _status_text(self, player_uuid: str, kit) -> str:
        remaining = self._cooldown_manager.get_remaining_seconds(
            player_uuid, kit.id, kit.metadata.cooldown_seconds
        )
        if remaining == 0:
            return "Siap diklaim"
        return format_duration(remaining, self._config.cooldown_time_format)
