from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KitItemData:
    """Representasi satu item di dalam kit, hasil serialisasi dari
    `ItemStack` milik Endstone menjadi bentuk yang JSON-serializable.

    Field ini SENGAJA disimpan generik (dict/list/str/int biasa, bukan
    objek Endstone langsung) supaya:
    1. Bisa ditulis ke `kits.json` tanpa perlu custom JSON encoder.
    2. Kalau API Endstone berubah, hanya `ItemSerializer` yang perlu
       disesuaikan -- model data ini tidak ikut berubah.
    """

    slot: int
    type: str  # identifier item, mis. "minecraft:diamond_sword"
    amount: int = 1
    display_name: Optional[str] = None
    lore: list = field(default_factory=list)
    damage: Optional[int] = None  # durability terpakai
    unbreakable: bool = False
    enchantments: dict = field(default_factory=dict)  # {"sharpness": 5}

    # Best-effort / informational -- lihat dokumen desain §1:
    # Bedrock tidak punya konsep "Custom Model Data" asli seperti Java,
    # jadi field ini tidak menjamin efek visual apa pun.
    custom_model_data: Optional[int] = None

    # SNBT (string) dari ItemStack.nbt, disimpan HANYA untuk referensi
    #/debug admin. TIDAK dipakai lagi saat deserialize -- lihat
    # catatan lengkap di `services/item_serializer.py`.
    raw_nbt: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "slot": self.slot,
            "type": self.type,
            "amount": self.amount,
            "display_name": self.display_name,
            "lore": list(self.lore),
            "damage": self.damage,
            "unbreakable": self.unbreakable,
            "enchantments": dict(self.enchantments),
            "custom_model_data": self.custom_model_data,
            "raw_nbt": self.raw_nbt,
        }

    @staticmethod
    def from_dict(data: dict) -> "KitItemData":
        return KitItemData(
            slot=data["slot"],
            type=data["type"],
            amount=data.get("amount", 1),
            display_name=data.get("display_name"),
            lore=list(data.get("lore", [])),
            damage=data.get("damage"),
            unbreakable=data.get("unbreakable", False),
            enchantments=dict(data.get("enchantments", {})),
            custom_model_data=data.get("custom_model_data"),
            raw_nbt=data.get("raw_nbt"),
        )
