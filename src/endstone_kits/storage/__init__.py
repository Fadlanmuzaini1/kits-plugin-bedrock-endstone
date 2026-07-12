"""
Akses fisik ke file/DB, mengikuti Repository Pattern.

Tidak ada business logic di folder ini -- hanya baca/tulis storage.
Semua kode di luar folder ini (terutama `managers/`) hanya boleh
bergantung pada interface di `storage/base.py`, bukan implementasi
konkret (`JsonKitRepository`, `SqliteCooldownRepository`) secara
langsung.
"""
