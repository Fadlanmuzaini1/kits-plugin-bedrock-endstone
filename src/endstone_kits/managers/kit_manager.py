"""
KitManager: satu-satunya business logic untuk CRUD kit.

Bergantung HANYA pada interface `KitRepository` (bukan implementasi
JSON konkret) supaya bisa diuji dengan mock storage tanpa server
Minecraft menyala -- lihat dokumen desain §2 prinsip #2.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, List, Optional

from endstone_kits.models.kit import Kit, KitMetadata
from endstone_kits.models.kit_command_entry import KitCommandEntry
from endstone_kits.storage.base import KitRepository

if TYPE_CHECKING:
    # Hanya untuk type hint -- tidak diimpor saat runtime (berkat
    # `from __future__ import annotations`), supaya file ini TIDAK
    # mewajibkan package `endstone` ter-install untuk diuji secara
    # unit test murni di luar server.
    from endstone.inventory import PlayerInventory


class KitManager:
    def __init__(self, repository: KitRepository):
        self._repository = repository
        self._cache: dict = {}  # dict[str, Kit]
        self._load()

    # ------------------------------------------------------------------
    # Loading & persistensi
    # ------------------------------------------------------------------
    def _load(self) -> None:
        data = self._repository.load_all()
        self._cache = {
            kit_id: Kit.from_dict(kit_id, kit_data)
            for kit_id, kit_data in data.get("kits", {}).items()
        }

    def _persist(self) -> None:
        """Write-through: setiap mutasi langsung ditulis ke storage,
        supaya tidak ada jendela waktu di mana data kit hanya ada di
        memory (lihat dokumen desain §2 prinsip #4)."""
        self._repository.save_all(
            {"kits": {kit_id: kit.to_dict() for kit_id, kit in self._cache.items()}}
        )

    def reload(self) -> None:
        """Muat ulang seluruh kit dari storage, membuang cache lama.
        Dipanggil oleh `/kit reload`."""
        self._load()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def get(self, kit_id: str) -> Optional[Kit]:
        return self._cache.get(kit_id)

    def exists(self, kit_id: str) -> bool:
        return kit_id in self._cache

    def list_all(self) -> List[Kit]:
        return list(self._cache.values())

    # ------------------------------------------------------------------
    # Mutasi
    # ------------------------------------------------------------------
    def create_from_inventory(
        self,
        kit_id: str,
        inventory: "PlayerInventory",
        cooldown_seconds: int,
        display_name: Optional[str] = None,
    ) -> Kit:
        """Buat kit baru; isi diambil langsung dari inventory admin.

        Permission OTOMATIS dibuat mengikuti pola `kits.<id>` (mis.
        kit "vip" -> permission "kits.vip"), supaya admin tidak perlu
        langkah tambahan `/kit permission` untuk kasus umum satu kit
        satu permission. Bisa DITIMPA belakangan lewat
        `/kit permission <id> <node>` kalau butuh pola berbeda (mis.
        beberapa kit berbagi 1 permission yang sama, atau kit tanpa
        permission sama sekali via `/kit permission <id> none`).

        CATATAN (lihat juga dokumen desain §1 & Tahap 4): karena kit
        (dan permission otomatisnya) dibuat saat RUNTIME lewat
        command -- bukan dideklarasikan statis saat plugin dimuat --
        node ini TIDAK otomatis terdaftar ke `plugin_manager.permissions`
        yang di-scan Prime BDS untuk UI rank editor-nya (API Endstone
        Python saat ini tidak menyediakan cara mendaftarkan Permission
        baru secara dinamis). Node TETAP berfungsi penuh untuk
        pengecekan akses (`has_permission` tidak mewajibkan
        pra-pendaftaran); admin hanya perlu tahu node persisnya
        (`kits.<id>`, bisa dicek lewat `/kit info <id>`) saat mengatur
        rank di Prime BDS, walau node itu mungkin tidak muncul di
        daftar/autocomplete UI-nya.
        """
        if self.exists(kit_id):
            raise ValueError(f"Kit '{kit_id}' sudah ada.")

        items = self._snapshot_inventory(inventory)
        kit = Kit(
            id=kit_id,
            metadata=KitMetadata(
                display_name=display_name or kit_id,
                permission=f"kits.{kit_id.lower()}",
                cooldown_seconds=max(0, cooldown_seconds),
            ),
            items=items,
        )
        self._cache[kit_id] = kit
        self._persist()
        return kit

    def edit_items_from_inventory(
        self, kit_id: str, inventory: "PlayerInventory"
    ) -> Kit:
        """Mengganti isi ITEM kit dengan snapshot inventory saat ini,
        TANPA menyentuh metadata (nama, deskripsi, permission,
        cooldown) atau command yang sudah diatur -- sesuai requirement
        "kit dapat diedit" (bukan dibuat ulang dari nol)."""
        kit = self._require(kit_id)
        kit.items = self._snapshot_inventory(inventory)
        kit.updated_at = int(time.time())
        self._persist()
        return kit

    def delete(self, kit_id: str) -> bool:
        if kit_id not in self._cache:
            return False
        del self._cache[kit_id]
        self._persist()
        return True

    def set_cooldown(self, kit_id: str, seconds: int) -> Kit:
        kit = self._require(kit_id)
        kit.metadata.cooldown_seconds = max(0, seconds)
        kit.updated_at = int(time.time())
        self._persist()
        return kit

    def set_description(self, kit_id: str, description: str) -> Kit:
        kit = self._require(kit_id)
        kit.metadata.description = description
        kit.updated_at = int(time.time())
        self._persist()
        return kit

    def set_one_time(self, kit_id: str, enabled: bool) -> Kit:
        kit = self._require(kit_id)
        kit.metadata.one_time = enabled
        kit.updated_at = int(time.time())
        self._persist()
        return kit

    def set_permission(self, kit_id: str, permission: Optional[str]) -> Kit:
        kit = self._require(kit_id)
        # Normalisasi ke lowercase: konvensi umum permission node
        # Bukkit-style memang lowercase, dan Prime BDS SECARA EKSPLISIT
        # me-lowercase semua nama permission saat menerapkannya ke
        # player (lihat `permission_manager.cpp: toLower(k)` di source
        # Prime BDS). Kalau admin mengetik node dengan huruf besar
        # (mis. "Kits.VIP") di sini tapi Prime BDS menerapkannya
        # sebagai "kits.vip", pengecekan `has_permission()` akan
        # mismatch akibat perbedaan case. Normalisasi di titik masuk
        # ini (satu-satunya tempat kit.metadata.permission ditulis)
        # menghilangkan risiko itu untuk semua kasus.
        kit.metadata.permission = permission.lower() if permission else None
        kit.updated_at = int(time.time())
        self._persist()
        return kit

    def grant_items_to(self, kit_id: str, player) -> list:
        """Berikan seluruh item kit ke inventory player.

        Return: list `ItemStack` yang TIDAK muat di inventory
        (leftover) -- dipakai command layer untuk memberi tahu player
        kalau inventory penuh. Tidak melempar exception untuk kasus
        ini (inventory penuh bukan error, hanya kondisi yang perlu
        diberi tahu ke player).
        """
        # Import lazy -- lihat alasan yang sama seperti di
        # `_snapshot_inventory`: supaya modul ini tetap importable
        # untuk unit test murni tanpa package `endstone`.
        from endstone_kits.services.item_serializer import ItemSerializer

        kit = self._require(kit_id)
        leftover: list = []
        for kit_item in kit.items:
            item_stack = ItemSerializer.deserialize(kit_item)
            not_added = player.inventory.add_item(item_stack)
            leftover.extend(not_added.values())
        return leftover

    def add_command(self, kit_id: str, template: str, run_as: str = "player") -> Kit:
        kit = self._require(kit_id)
        kit.commands.append(KitCommandEntry(template=template, run_as=run_as))
        kit.updated_at = int(time.time())
        self._persist()
        return kit

    def remove_command(self, kit_id: str, index: int) -> Kit:
        """`index` berbasis 0 di sini -- konversi dari input user
        (biasanya 1-based, lebih ramah admin) dilakukan di command
        layer, bukan di sini."""
        kit = self._require(kit_id)
        if index < 0 or index >= len(kit.commands):
            raise ValueError(
                f"Index command tidak valid untuk kit '{kit_id}' "
                f"(jumlah command saat ini: {len(kit.commands)})."
            )
        del kit.commands[index]
        kit.updated_at = int(time.time())
        self._persist()
        return kit

    # ------------------------------------------------------------------
    # Helper privat
    # ------------------------------------------------------------------
    def _require(self, kit_id: str) -> Kit:
        kit = self._cache.get(kit_id)
        if kit is None:
            raise ValueError(f"Kit '{kit_id}' tidak ditemukan.")
        return kit

    @staticmethod
    def _snapshot_inventory(inventory: "PlayerInventory") -> list:
        # Import lazy: modul ini butuh `endstone.inventory.ItemStack`
        # secara transitif, yang hanya tersedia saat plugin benar-benar
        # berjalan di server. Dengan mengimpornya di sini (bukan di
        # bagian atas file), `KitManager` tetap bisa diimpor & diuji
        # (create/delete/list/cooldown/permission) tanpa package
        # `endstone` ter-install -- hanya alur yang benar-benar
        # menyentuh inventory sungguhan yang butuh endstone aktif.
        from endstone_kits.services.item_serializer import ItemSerializer

        items = []
        for slot, item in enumerate(inventory.contents):
            if item is None:
                continue
            items.append(ItemSerializer.serialize(slot, item))
        return items
