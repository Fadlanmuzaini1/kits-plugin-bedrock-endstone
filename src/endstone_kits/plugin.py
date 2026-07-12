from __future__ import annotations

from pathlib import Path
from typing import Optional

from endstone import Player
from endstone.command import Command, CommandSender
from endstone.plugin import Plugin

from endstone_kits.commands.kit_admin_command import KitAdminCommands
from endstone_kits.commands.kit_command import KitPlayerCommands
from endstone_kits.config.config_schema import KitsConfig
from endstone_kits.listeners.player_listener import PlayerListener
from endstone_kits.managers.command_execution_manager import CommandExecutionManager
from endstone_kits.managers.cooldown_manager import CooldownManager
from endstone_kits.managers.gui_manager import GUIManager
from endstone_kits.managers.kit_manager import KitManager
from endstone_kits.managers.permission_manager import PermissionManager
from endstone_kits.services.permission_provider import NativePermissionProvider
from endstone_kits.storage.json_kit_repository import JsonKitRepository
from endstone_kits.storage.sqlite_cooldown_repository import SqliteCooldownRepository


class KitsPlugin(Plugin):
    """Kelas utama plugin.

    PENTING: kelas ini adalah *composition root* -- tugasnya HANYA
    merangkai (wire) komponen: load config, buka storage, buat
    manager, daftarkan listener, lalu menyuntikkan semuanya ke handler
    command. Kelas ini SENGAJA tidak diisi business logic apa pun;
    itu semua tanggung jawab `managers/`.
    """

    api_version = "0.6"

    name = "Kits"
    version = "0.6.0"
    description = (
        "Sistem kit (item + command) dengan cooldown per-player, "
        "integrasi permission, dan GUI form."
    )
    prefix = "Kits"  # prefix untuk log plugin (bukan prefix pesan in-game)

    # ------------------------------------------------------------------
    # Metadata command & permission.
    #
    # Tahap 4: pengecekan permission PER-KIT sudah aktif di `/kit list`
    # (filter) & `/kit claim` (blokir kalau tidak punya izin). Node
    # `kits.vip`/`kits.mvp`/`kits.staff` didaftarkan di sini sebagai
    # CONTOH (sesuai requirement awal) supaya otomatis terdeteksi &
    # bisa diatur lewat rank editor Prime BDS -- lihat catatan lengkap
    # di `services/permission_provider.py`. Admin bebas memakai node
    # lain lewat `/kit permission <id> <node>`; node custom TETAP
    # berfungsi untuk pengecekan, hanya saja mungkin tidak otomatis
    # muncul di rank editor Prime BDS kalau belum pernah dideklarasikan
    # oleh plugin manapun.
    # ------------------------------------------------------------------
    commands = {
        "kit": {
            "description": "Perintah utama plugin Kits.",
            "usages": [
                "/kit",
                "/kit list",
                "/kit info <id: string>",
                "/kit claim <id: string>",
                "/kit reload",
                "/kit create <id: string> <cooldown_seconds: int> [display_name: message]",
                "/kit edit <id: string>",
                "/kit delete <id: string>",
                "/kit cooldown <id: string> <seconds: int>",
                "/kit permission <id: string> [node: string]",
                "/kit description <id: string> <text: message>",
                "/kit onetime <id: string> <true_or_false: string>",
                "/kit addcommand <id: string> <player_or_console: string> <command: message>",
                "/kit removecommand <id: string> <index: int>",
            ],
            # PENTING: HANYA `kits.use` di sini -- ini gerbang MINIMUM
            # supaya command `/kit` bisa dipanggil sama sekali. Endstone
            # mewajibkan sender punya SEMUA permission yang terdaftar di
            # sini (AND, bukan OR seperti Bukkit) sebelum request masuk
            # ke `on_command`. Kalau semua node admin ikut dicantumkan
            # di sini, player biasa (yang hanya punya `kits.use`) akan
            # ditolak Endstone SEBELUM sempat mencapai `on_command` --
            # itulah yang menyebabkan player non-op tidak bisa memakai
            # `/kit` sama sekali. Pengecekan permission PER sub-command
            # (mis. `kits.admin.create` khusus untuk `/kit create`)
            # tetap dilakukan manual lewat `_guarded()` di `on_command`.
            "permissions": ["kits.use"],
        }
    }

    permissions = {
        "kits.use": {
            "description": "Izin dasar untuk menggunakan perintah /kit.",
            "default": True,
        },
        "kits.admin.reload": {
            "description": "Izin untuk me-reload konfigurasi & data plugin.",
            "default": "op",
        },
        "kits.admin.create": {
            "description": "Izin untuk membuat kit baru dari inventory.",
            "default": "op",
        },
        "kits.admin.edit": {
            "description": "Izin untuk mengedit isi kit yang sudah ada.",
            "default": "op",
        },
        "kits.admin.delete": {
            "description": "Izin untuk menghapus kit.",
            "default": "op",
        },
        "kits.admin.cooldown": {
            "description": "Izin untuk mengatur cooldown kit.",
            "default": "op",
        },
        "kits.admin.permission": {
            "description": "Izin untuk mengatur permission node kit.",
            "default": "op",
        },
        "kits.admin.description": {
            "description": "Izin untuk mengatur deskripsi kit.",
            "default": "op",
        },
        "kits.admin.onetime": {
            "description": "Izin untuk mengatur status sekali-pakai kit.",
            "default": "op",
        },
        "kits.admin.command": {
            "description": "Izin untuk menambah/menghapus command isi kit.",
            "default": "op",
        },
        # Node CONTOH untuk kit per-rank, sesuai requirement awal.
        # Default False -- HARUS digrant eksplisit lewat rank editor
        # Prime BDS (atau plugin permission lain / op) supaya tidak
        # ada player biasa yang otomatis kebagian kit VIP/MVP/staff.
        "kits.vip": {
            "description": "Contoh izin untuk kit tier VIP.",
            "default": False,
        },
        "kits.mvp": {
            "description": "Contoh izin untuk kit tier MVP.",
            "default": False,
        },
        "kits.staff": {
            "description": "Contoh izin untuk kit tier staff.",
            "default": False,
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._kits_config: Optional[KitsConfig] = None
        self._kit_repository: Optional[JsonKitRepository] = None
        self._cooldown_repository: Optional[SqliteCooldownRepository] = None
        self._kit_manager: Optional[KitManager] = None
        self._cooldown_manager: Optional[CooldownManager] = None
        self._permission_manager: Optional[PermissionManager] = None
        self._command_execution_manager: Optional[CommandExecutionManager] = None
        self._player_commands: Optional[KitPlayerCommands] = None
        self._admin_commands: Optional[KitAdminCommands] = None
        self._gui_manager: Optional[GUIManager] = None
        self._player_listener: Optional[PlayerListener] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def on_load(self) -> None:
        self.logger.info("Kits: plugin sedang dimuat...")

    def on_enable(self) -> None:
        self._load_config()
        self._init_storage()
        self._init_managers()
        self._init_command_handlers()
        self._init_gui()
        self._init_listeners()

        prime_bds_detected = PermissionManager.detect_prime_bds(self.server)
        if prime_bds_detected:
            self.logger.info(
                "Kits: Prime BDS terdeteksi -- permission kit akan mengikuti "
                "rank/permission yang diatur lewat Prime BDS secara otomatis."
            )
        else:
            self.logger.info(
                "Kits: Prime BDS tidak terdeteksi -- permission kit memakai "
                "sistem permission native Endstone (op / permission plugin lain)."
            )

        self.logger.info(
            f"Kits: plugin aktif. {len(self._kit_manager.list_all())} kit dimuat "
            f"dari {self._kits_config.kits_file}."
        )

    def on_disable(self) -> None:
        if self._cooldown_repository is not None:
            self._cooldown_repository.close()
        self.logger.info("Kits: plugin dimatikan.")

    # ------------------------------------------------------------------
    # Wiring helpers (dipanggil dari on_enable, dipisah agar mudah
    # dibaca & tiap tahap punya "tempatnya sendiri")
    # ------------------------------------------------------------------
    def _load_config(self) -> None:
        # save_default_config() menyalin config.toml bawaan (resource
        # yang dibundel di package ini) ke folder data plugin, HANYA
        # jika file belum ada di sana -- aman dipanggil setiap start.
        self.save_default_config()
        self._kits_config = KitsConfig(self.config)

    def _init_storage(self) -> None:
        data_folder = Path(self.data_folder)
        data_folder.mkdir(parents=True, exist_ok=True)

        kits_path = data_folder / self._kits_config.kits_file
        db_path = data_folder / self._kits_config.database_file

        self._kit_repository = JsonKitRepository(kits_path)
        self._cooldown_repository = SqliteCooldownRepository(
            db_path, wal_mode=self._kits_config.sqlite_wal_mode
        )

    def _init_managers(self) -> None:
        self._kit_manager = KitManager(self._kit_repository)
        self._cooldown_manager = CooldownManager(self._cooldown_repository)
        self._permission_manager = PermissionManager(NativePermissionProvider(), self)
        self._command_execution_manager = CommandExecutionManager(self.server)

    def _init_command_handlers(self) -> None:
        self._player_commands = KitPlayerCommands(
            self._kit_manager,
            self._cooldown_manager,
            self._permission_manager,
            self._command_execution_manager,
            self._kits_config,
            logger=self.logger,
        )
        self._admin_commands = KitAdminCommands(self._kit_manager, self._kits_config)

    def _init_gui(self) -> None:
        self._gui_manager = GUIManager(
            self._kit_manager,
            self._cooldown_manager,
            self._permission_manager,
            self._player_commands,
            self._kits_config,
        )

    def _init_listeners(self) -> None:
        self._player_listener = PlayerListener(self._cooldown_manager)
        self.register_events(self._player_listener)

    # ------------------------------------------------------------------
    # Command handling
    #
    # Router ini SENGAJA tetap tipis: hanya menentukan sub-command mana
    # yang dipanggil dan permission apa yang dibutuhkan. Detail parsing
    # argumen & pesan ada di `KitPlayerCommands`/`KitAdminCommands`.
    # ------------------------------------------------------------------
    def on_command(
        self, sender: CommandSender, command: Command, args: list
    ) -> bool:
        if command.name != "kit":
            return False

        if not args:
            return self._guarded(sender, "kits.use", self._open_default_view)

        sub = args[0].lower()
        rest = args[1:]

        if sub == "reload":
            return self._handle_reload(sender)
        elif sub == "list":
            return self._guarded(sender, "kits.use", self._player_commands.list_kits)
        elif sub == "info":
            return self._guarded(
                sender, "kits.use", lambda s: self._require_arg_info(s, rest)
            )
        elif sub == "claim":
            return self._guarded(
                sender, "kits.use", lambda s: self._player_commands.claim(s, rest)
            )
        elif sub == "create":
            return self._guarded(
                sender, "kits.admin.create", lambda s: self._admin_commands.create(s, rest)
            )
        elif sub == "edit":
            return self._guarded(
                sender, "kits.admin.edit", lambda s: self._admin_commands.edit(s, rest)
            )
        elif sub == "delete":
            return self._guarded(
                sender, "kits.admin.delete", lambda s: self._admin_commands.delete(s, rest)
            )
        elif sub == "cooldown":
            return self._guarded(
                sender,
                "kits.admin.cooldown",
                lambda s: self._admin_commands.cooldown(s, rest),
            )
        elif sub == "permission":
            return self._guarded(
                sender,
                "kits.admin.permission",
                lambda s: self._admin_commands.permission(s, rest),
            )
        elif sub == "description":
            return self._guarded(
                sender,
                "kits.admin.description",
                lambda s: self._admin_commands.description(s, rest),
            )
        elif sub == "onetime":
            return self._guarded(
                sender,
                "kits.admin.onetime",
                lambda s: self._admin_commands.onetime(s, rest),
            )
        elif sub == "addcommand":
            return self._guarded(
                sender,
                "kits.admin.command",
                lambda s: self._admin_commands.addcommand(s, rest),
            )
        elif sub == "removecommand":
            return self._guarded(
                sender,
                "kits.admin.command",
                lambda s: self._admin_commands.removecommand(s, rest),
            )

        sender.send_message(
            f"{self._kits_config.prefix}Sub-command tidak dikenal: {sub}"
        )
        return True

    # ------------------------------------------------------------------
    def _guarded(self, sender: CommandSender, permission: str, action) -> bool:
        if not sender.has_permission(permission):
            sender.send_message(
                f"{self._kits_config.prefix}"
                f"{self._kits_config.message('no_permission')}"
            )
            return True
        action(sender)
        return True

    def _require_arg_info(self, sender: CommandSender, rest: list) -> None:
        if not rest:
            sender.send_message(f"{self._kits_config.prefix}Gunakan: /kit info <id>")
            return
        self._player_commands.info(sender, rest[0])

    def _open_default_view(self, sender: CommandSender) -> None:
        """Dipanggil saat `/kit` dijalankan tanpa argumen. Buka GUI
        kalau sender adalah Player DAN GUI diaktifkan di config;
        selain itu (console, atau GUI dimatikan admin) fallback ke
        daftar teks biasa -- supaya command tetap berguna di kedua
        skenario tanpa membedakan cara pemakaian di dokumentasi."""
        if isinstance(sender, Player) and self._kits_config.gui_enabled:
            self._gui_manager.open_kit_list(sender)
        else:
            self._player_commands.list_kits(sender)

    def _handle_reload(self, sender: CommandSender) -> bool:
        if not sender.has_permission("kits.admin.reload"):
            sender.send_message(
                f"{self._kits_config.prefix}"
                f"{self._kits_config.message('no_permission')}"
            )
            return True

        self.reload_config()
        self._kits_config = KitsConfig(self.config)
        self._kit_manager.reload()
        # CooldownManager TIDAK direset di sini -- cooldown adalah
        # state live (bukan "definisi" seperti kit), cache yang sudah
        # ada tetap valid dan tidak perlu dimuat ulang dari database.
        # Handler command menyimpan referensi ke config lama secara
        # langsung, jadi perlu dibuat ulang supaya ikut memakai
        # instance KitsConfig yang baru. GUIManager juga menyimpan
        # referensi ke `player_commands` lama, jadi ikut dibuat ulang.
        self._init_command_handlers()
        self._init_gui()

        sender.send_message(
            f"{self._kits_config.prefix}Konfigurasi & data kit berhasil dimuat ulang."
        )
        return True
