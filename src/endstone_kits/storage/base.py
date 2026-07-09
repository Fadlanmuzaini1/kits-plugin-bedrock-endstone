"""
Interface (abstrak) untuk lapisan penyimpanan.

Aturan penting: kode di `managers/` HANYA boleh bergantung pada
interface di file ini (`KitRepository`, `CooldownRepository`), TIDAK
PERNAH pada implementasi konkret (`JsonKitRepository`,
`SqliteCooldownRepository`) secara langsung. Dengan begitu, storage
bisa diganti (mis. JSON -> SQLite penuh di masa depan) tanpa
menyentuh satu baris pun business logic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class KitRepository(ABC):
    """Menyimpan definisi kit (metadata, item, command).

    Data direpresentasikan sebagai dict polos (JSON-serializable) pada
    tahap ini karena model `Kit` (dataclass) baru dibangun di Tahap 2.
    Kontrak ini sengaja dibuat generik di level dict supaya Tahap 2
    tinggal menambahkan fungsi serialize/deserialize `Kit` <-> dict di
    `KitManager`, tanpa perlu mengubah interface repository ini.
    """

    @abstractmethod
    def load_all(self) -> dict:
        """Mengembalikan seluruh data kit.

        Struktur: {"kits": {<kit_id>: {...definisi kit...}, ...}}
        """
        raise NotImplementedError

    @abstractmethod
    def save_all(self, data: dict) -> None:
        """Menulis seluruh data kit ke storage (menimpa isi lama)."""
        raise NotImplementedError


class CooldownRepository(ABC):
    """Menyimpan cooldown per-player per-kit."""

    @abstractmethod
    def get_all_for_player(self, player_uuid: str) -> dict[str, int]:
        """Mengembalikan {kit_id: last_claimed_epoch_seconds} milik
        satu player. Dipakai untuk lazy-load cache saat player join."""
        raise NotImplementedError

    @abstractmethod
    def upsert(self, player_uuid: str, kit_id: str, last_claimed_at: int) -> None:
        """Menyimpan/mengupdate waktu klaim terakhir untuk kombinasi
        1 player + 1 kit."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Menutup koneksi/resource storage. Dipanggil saat plugin
        disable agar tidak ada file handle yang menggantung."""
        raise NotImplementedError
