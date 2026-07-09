"""
Business logic murni: KitManager, CooldownManager, PermissionManager,
CommandExecutionManager, GUIManager.

Manager TIDAK PERNAH mengimpor implementasi storage/service konkret
secara langsung -- hanya interface dari `storage/base.py` dan
`services/`, disuntikkan lewat constructor (dependency injection),
supaya bisa diuji dengan mock tanpa server Minecraft menyala.
"""
