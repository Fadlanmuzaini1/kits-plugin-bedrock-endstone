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
    def __init__(self, provider, plugin=None):
        self._provider = provider
        # `plugin` HANYA dibutuhkan untuk `revoke_permission()` --
        # Endstone mewajibkan identitas plugin pemilik saat membuat
        # PermissionAttachment baru. Opsional (default None) supaya
        # class ini tetap gampang diuji tanpa objek Plugin sungguhan
        # untuk kasus `can_access()` saja.
        self._plugin = plugin

    def can_access(self, sender, kit) -> bool:
        """Kit tanpa permission (`kit.metadata.permission is None`)
        bisa diakses siapa saja -- pengecekan izin dasar `kits.use`
        tetap dilakukan terpisah di layer command."""
        if kit.metadata.permission is None:
            return True
        return self._provider.has_permission(sender, kit.metadata.permission)

    def revoke_permission(self, player, node: str) -> None:
        """Cabut 1 permission node dari SATU player tertentu (dipakai
        setelah klaim kit one-time), dengan menambahkan
        `PermissionAttachment` milik plugin ini yang men-set node
        tsb ke False untuk player itu saja.

        PERINGATAN -- baca sebelum mengandalkan ini untuk logic apa
        pun yang penting: INI BUKAN mekanisme yang reliable untuk
        "melarang klaim ulang". Proteksi klaim ulang kit one-time
        TETAP sepenuhnya ditangani oleh
        `CooldownManager.has_ever_claimed()`, yang independen dari
        status permission apa pun. Attachment yang ditambahkan di
        sini bisa DITIMPA ULANG oleh Prime BDS (atau plugin permission
        lain) kapan pun ia menghitung ulang permission player --
        misalnya saat player rejoin, atau saat admin mengedit rank di
        Prime BDS, permission itu akan otomatis ter-grant lagi sesuai
        rank (attachment Prime BDS sendiri akan menggantikan attachment
        ini). Anggap fitur ini sebagai efek samping best-effort/
        kosmetik (\"biar kelihatan sudah dicabut\" di command permission
        Anda), BUKAN boundary keamanan.
        """
        if self._plugin is None or not node:
            return
        try:
            player.add_attachment(self._plugin, node, False)
        except Exception:
            # Jangan sampai kegagalan mencabut permission (mis. API
            # berubah, atau player sudah quit di tengah proses)
            # menggagalkan seluruh alur klaim yang sudah berhasil.
            pass

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
