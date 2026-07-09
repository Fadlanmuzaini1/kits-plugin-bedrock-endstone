"""
PermissionManager: satu-satunya business logic untuk menentukan apakah
seorang player boleh mengakses/klaim sebuah kit.

Bergantung pada `PermissionProvider` (bukan langsung `sender.has_permission`)
demi konsistensi dengan prinsip desain #2 -- lihat catatan lengkap di
`services/permission_provider.py` soal kenapa TIDAK ADA provider
khusus Prime BDS yang perlu ditulis terpisah.
"""
from __future__ import annotations


class PermissionManager:
    def __init__(self, provider):
        self._provider = provider

    def can_access(self, sender, kit) -> bool:
        """Kit tanpa permission (`kit.metadata.permission is None`)
        bisa diakses siapa saja -- pengecekan izin dasar `kits.use`
        tetap dilakukan terpisah di layer command."""
        if kit.metadata.permission is None:
            return True
        return self._provider.has_permission(sender, kit.metadata.permission)

    @staticmethod
    def detect_prime_bds(server) -> bool:
        """HANYA dipakai untuk log informatif saat plugin enable --
        lihat catatan di `services/permission_provider.py` kenapa
        hasil deteksi ini TIDAK memengaruhi provider yang dipakai
        (selalu `NativePermissionProvider`, apa pun hasilnya)."""
        try:
            plugin = server.plugin_manager.get_plugin("PrimeBDS")
            return plugin is not None
        except Exception:
            return False
