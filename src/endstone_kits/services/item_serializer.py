"""
Konversi ItemStack (Endstone) <-> KitItemData (dict JSON-serializable).

Ini SATU-SATUNYA tempat di seluruh plugin yang boleh tahu detail
representasi `ItemStack`/`ItemMeta` milik Endstone. Kalau API Endstone
berubah (lihat catatan versi di dokumen desain §1 -- API enchantment
khususnya masih berkembang), cukup file ini yang perlu disesuaikan;
`KitManager` dan model data lain tidak perlu berubah.

Referensi API yang dipakai (dicek terhadap endstone.dev/latest):
- `ItemStack(type: str, amount: int = 1, data: int = 0)`
- `ItemStack.item_meta` -> mengembalikan SALINAN ItemMeta (bukan
  referensi!) -- perubahan pada objek ini HARUS di-apply balik lewat
  `ItemStack.set_item_meta(meta)`.
- `ItemMeta.enchants` -> dict[Enchantment, int] (key berupa OBJEK
  Enchantment, bukan string) -- perlu dikonversi ke string id untuk
  disimpan sebagai JSON.
- `ItemMeta.add_enchant(id: str, level: int, force: bool = False)`
  menerima string id secara langsung.
"""
from __future__ import annotations

from typing import Optional

from endstone.inventory import ItemStack

from endstone_kits.models.kit_item import KitItemData


class ItemSerializer:
    @staticmethod
    def serialize(slot: int, item: ItemStack) -> KitItemData:
        """Ambil snapshot lengkap 1 `ItemStack` (dari inventory admin)
        menjadi `KitItemData` yang aman disimpan sebagai JSON."""
        meta = item.item_meta  # SALINAN -- aman dibaca, tidak akan
        # mengubah item asli di inventory admin.

        display_name = meta.display_name if meta.has_display_name else None
        lore = list(meta.lore) if meta.has_lore else []
        damage = meta.damage if meta.has_damage else None
        unbreakable = bool(meta.is_unbreakable)

        enchantments: dict = {}
        if meta.has_enchants:
            for enchant, level in meta.enchants.items():
                enchantments[ItemSerializer._enchant_id_to_str(enchant)] = level

        # Custom Model Data: lihat dokumen desain §1 -- Bedrock tidak
        # punya padanan asli untuk konsep ini, jadi tidak diisi di
        # sini secara otomatis (selalu None dari hasil serialize).
        custom_model_data = None

        # NBT mentah: HANYA disimpan sebagai referensi/debug untuk
        # admin. Lihat catatan lengkap di `deserialize()` kenapa ini
        # tidak dipakai lagi untuk merekonstruksi item.
        raw_nbt: Optional[str] = None
        try:
            if item.nbt is not None:
                raw_nbt = str(item.nbt)
        except Exception:
            # Sebagian tipe item mungkin tidak punya nbt yang bisa
            # dibaca dengan aman -- jangan sampai proses pembuatan kit
            # gagal total gara-gara ini.
            raw_nbt = None

        return KitItemData(
            slot=slot,
            type=str(item.type.id),
            amount=item.amount,
            display_name=display_name,
            lore=lore,
            damage=damage,
            unbreakable=unbreakable,
            enchantments=enchantments,
            custom_model_data=custom_model_data,
            raw_nbt=raw_nbt,
        )

    @staticmethod
    def deserialize(kit_item: KitItemData) -> ItemStack:
        """Bangun ulang `ItemStack` dari `KitItemData` (dipakai saat
        kit diklaim, dan saat menampilkan preview kit).

        CATATAN PENTING: `raw_nbt` TIDAK dipakai untuk merekonstruksi
        NBT mentah di sini -- API Endstone saat ini belum menyediakan
        cara yang terverifikasi aman untuk parse string SNBT kembali
        menjadi `CompoundTag` tanpa risiko merusak tag internal item
        (mis. struktur khusus block entity/banner pattern/dll). Field
        yang direkonstruksi HANYA yang tercakup `ItemMeta` (nama
        tampilan, lore, damage, enchant, unbreakable) -- ini sudah
        mencakup seluruh requirement metadata utama. Ini adalah
        keterbatasan yang diketahui, bukan bug.
        """
        item = ItemStack(kit_item.type, kit_item.amount)
        meta = item.item_meta

        if kit_item.display_name:
            meta.display_name = kit_item.display_name
        if kit_item.lore:
            meta.lore = list(kit_item.lore)
        if kit_item.damage is not None:
            meta.damage = kit_item.damage
        if kit_item.unbreakable:
            meta.is_unbreakable = True

        for enchant_id, level in kit_item.enchantments.items():
            try:
                # force=True: kit adalah item "custom" yang sengaja
                # dibuat admin -- jangan sampai level enchant admin
                # ditolak hanya karena melebihi batas level vanilla.
                meta.add_enchant(enchant_id, level, force=True)
            except Exception:
                # Satu enchant tidak valid (id salah ketik, atau tidak
                # berlaku untuk tipe item ini) tidak boleh menggagalkan
                # seluruh proses pemberian kit -- item tetap diberikan
                # tanpa enchant tsb saja.
                continue

        item.set_item_meta(meta)
        return item

    @staticmethod
    def _enchant_id_to_str(enchant) -> str:
        """API enchantment Endstone masih berkembang (lihat dokumen
        desain §1) -- beberapa versi mengekspos id lewat `.id`. Coba
        itu dulu, fallback ke `str()` supaya tidak crash kalau versi
        yang terpasang berbeda."""
        try:
            return str(enchant.id)
        except AttributeError:
            return str(enchant)
