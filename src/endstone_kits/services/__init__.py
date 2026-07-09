"""
Adapter ke sistem eksternal atau API Endstone yang spesifik/detail:
ItemSerializer (ItemStack <-> dict), PlaceholderService, dan
PermissionProvider (abstraksi ke Prime BDS / permission native).

Dipisah dari `managers/` supaya kalau API eksternal berubah, dampaknya
terlokalisasi di sini saja.
"""
