"""
KitsConfig membungkus dict `self.config` bawaan Endstone (hasil parse
config.toml) dengan properti bertipe.

Alasan kelas ini ada (bukan cukup pakai dict mentah):
1. Kalau struktur config.toml berubah di masa depan (mis. field
   dipindah/di-rename), cukup 1 file ini yang disentuh -- pemanggil
   (`KitsConfig(...).prefix`) tidak perlu berubah.
2. `_merge_defaults` memastikan config lama (dari instalasi sebelum
   update plugin) tidak menyebabkan KeyError saat field baru
   ditambahkan di versi plugin berikutnya.
"""
from __future__ import annotations

from endstone_kits.utils.color import translate_color_codes

DEFAULT_CONFIG: dict = {
    "prefix": "&8[&bKits&8] &r",
    "messages": {
        "no_permission": "&cKamu tidak punya izin untuk kit ini.",
        "cooldown_active": "&eTunggu {time} lagi sebelum klaim ulang.",
        "kit_claimed": "&aKamu berhasil klaim kit {kit}.",
        "kit_not_found": "&cKit '{kit}' tidak ditemukan.",
        "kit_created": "&aKit '{kit}' berhasil dibuat.",
        "claim_in_progress": "&eKlaim sebelumnya masih diproses, coba lagi sebentar.",
        "inventory_full": "&eInventory penuh, {count} stack item tidak muat dan hilang.",
        "kit_already_claimed": "&cKit ini hanya bisa diklaim sekali, dan kamu sudah pernah mengklaimnya.",
    },
    "cooldown": {
        "time_format": "long",
    },
    "gui": {
        "enabled": True,
        "title": "Daftar Kit",
        "show_permission_in_lore": True,
        "show_time_remaining": True,
    },
    "storage": {
        "kits_file": "kits.json",
        "database_file": "cooldowns.db",
        "sqlite_wal_mode": True,
    },
    "permissions": {
        "provider": "auto",
    },
}


def _merge_defaults(loaded: dict, defaults: dict) -> dict:
    """Deep-merge: nilai dari `loaded` menang atas `defaults`, tapi key
    yang belum ada di `loaded` diisi dari `defaults`. Rekursif untuk
    nested dict (mis. `messages`, `gui`, `storage`)."""
    merged = dict(defaults)
    for key, value in (loaded or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_defaults(value, merged[key])
        else:
            merged[key] = value
    return merged


class KitsConfig:
    def __init__(self, raw: dict):
        self._raw = _merge_defaults(raw, DEFAULT_CONFIG)

    # --- Umum ---------------------------------------------------------
    @property
    def prefix(self) -> str:
        # Admin menulis "&b" dkk di config.toml; di-translate ke "§b"
        # (format asli Bedrock) di sini -- satu-satunya tempat
        # translasi terjadi. Lihat `utils/color.py` untuk alasannya.
        return translate_color_codes(self._raw["prefix"])

    def message(self, key: str) -> str:
        """Ambil template pesan berdasarkan key (sudah ditranslate ke
        kode warna § Bedrock), kembalikan string kosong kalau key
        tidak dikenal (fail-safe, bukan KeyError)."""
        raw = self._raw.get("messages", {}).get(key, "")
        return translate_color_codes(raw)

    # --- Cooldown -------------------------------------------------------
    @property
    def cooldown_time_format(self) -> str:
        return self._raw["cooldown"]["time_format"]

    # --- GUI --------------------------------------------------------------
    @property
    def gui_enabled(self) -> bool:
        return self._raw["gui"]["enabled"]

    @property
    def gui_title(self) -> str:
        return self._raw["gui"]["title"]

    @property
    def gui_show_permission_in_lore(self) -> bool:
        return self._raw["gui"]["show_permission_in_lore"]

    @property
    def gui_show_time_remaining(self) -> bool:
        return self._raw["gui"]["show_time_remaining"]

    # --- Storage ------------------------------------------------------
    @property
    def kits_file(self) -> str:
        return self._raw["storage"]["kits_file"]

    @property
    def database_file(self) -> str:
        return self._raw["storage"]["database_file"]

    @property
    def sqlite_wal_mode(self) -> bool:
        return self._raw["storage"]["sqlite_wal_mode"]

    # --- Permission -----------------------------------------------------
    @property
    def permission_provider(self) -> str:
        return self._raw["permissions"]["provider"]
