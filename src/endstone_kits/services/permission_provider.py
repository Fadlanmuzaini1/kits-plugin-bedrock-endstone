"""
Abstraksi pengecekan permission.

TEMUAN PENTING (Tahap 4): setelah membaca source code resmi Prime BDS
(https://github.com/PrimeStrat/primebds -- plugin C++ untuk Endstone),
ternyata Prime BDS TIDAK mengekspos API/service terpisah untuk plugin
lain memeriksa permission. Prime BDS bekerja dengan menerapkan
permission LANGSUNG ke sistem `Permissible` bawaan Endstone milik
setiap player:

    player.addAttachment(*this, "primebdsoverride", true);
    attachment->setPermission(perm, value);
    player.recalculatePermissions();

(lihat `src/plugin.cpp` di repo Prime BDS) -- berdasarkan rank yang
dikonfigurasi admin lewat Prime BDS sendiri.

Artinya: `sender.has_permission("kits.vip")` (API NATIVE Endstone yang
PERSIS SAMA seolah tidak ada plugin permission apa pun) SUDAH otomatis
mencerminkan keputusan Prime BDS -- TIDAK ADA kode integrasi khusus
yang perlu ditulis untuk Prime BDS. Ini berbeda dari asumsi awal di
dokumen desain §1 yang mengira perlu `PrimeBDSPermissionProvider`
terpisah; setelah membaca source code aslinya, provider seperti itu
tidak diperlukan sama sekali.

`PermissionProvider` di bawah tetap dibuat sebagai abstraksi (bukan
memanggil `sender.has_permission` tersebar di banyak file) semata
untuk:
1. Konsisten dengan prinsip desain #2 (manager tidak memanggil
   Endstone API secara langsung).
2. Titik ekstensi kalau di masa depan dibutuhkan provider lain yang
   BENAR-BENAR punya API terpisah (mis. plugin permission yang tidak
   mengikuti pola Bukkit-style Permissible).

CATATAN TAMBAHAN soal visibilitas node custom di Prime BDS: Prime BDS
men-scan `plugin_manager.permissions` (permission yang dideklarasikan
tiap plugin lewat `permissions = {...}` di class Plugin) untuk
menentukan node mana yang muncul & bisa diatur di rank editor-nya
(lihat `permission_manager.cpp: loadPermissions()` di repo Prime BDS).
Karena itu, node CONTOH dari requirement awal (`kits.vip`, `kits.mvp`,
`kits.staff`) sengaja DIDEKLARASIKAN di `KitsPlugin.permissions` (lihat
`plugin.py`) supaya otomatis terlihat & bisa diatur admin di rank
editor Prime BDS. Node custom yang admin ketik bebas lewat
`/kit permission <id> <node>` TETAP BERFUNGSI untuk pengecekan
(`has_permission` tidak mewajibkan node terdaftar dulu), tapi mungkin
tidak muncul di UI rank editor Prime BDS kalau node itu belum pernah
dideklarasikan oleh plugin manapun.
"""
from __future__ import annotations

from typing import Protocol


class PermissionProvider(Protocol):
    def has_permission(self, sender, node: str) -> bool: ...


class NativePermissionProvider:
    """Memakai `Permissible.has_permission()` bawaan Endstone secara
    langsung. Ini SATU-SATUNYA provider yang dibutuhkan untuk Prime
    BDS (lihat catatan panjang di atas) maupun plugin permission lain
    yang mengikuti pola serupa (menerapkan permission ke Permissible,
    bukan expose API terpisah -- ini konvensi umum plugin bergaya
    Bukkit/LuckPerms)."""

    def has_permission(self, sender, node: str) -> bool:
        return sender.has_permission(node)
