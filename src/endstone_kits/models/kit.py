from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from endstone_kits.models.kit_command_entry import KitCommandEntry
from endstone_kits.models.kit_item import KitItemData


@dataclass
class KitMetadata:
    display_name: str
    description: str = ""
    icon: Optional[str] = None
    permission: Optional[str] = None  # None = semua orang boleh klaim
    cooldown_seconds: int = 0  # 0 = tanpa cooldown

    def to_dict(self) -> dict:
        return {
            "display_name": self.display_name,
            "description": self.description,
            "icon": self.icon,
            "permission": self.permission,
            "cooldown_seconds": self.cooldown_seconds,
        }

    @staticmethod
    def from_dict(data: dict) -> "KitMetadata":
        return KitMetadata(
            display_name=data["display_name"],
            description=data.get("description", ""),
            icon=data.get("icon"),
            permission=data.get("permission"),
            cooldown_seconds=data.get("cooldown_seconds", 0),
        )


@dataclass
class Kit:
    """Representasi lengkap 1 kit: metadata + item + command.

    `id` bersifat immutable secara konvensi (dipakai sebagai key di
    dict cache `KitManager` maupun sebagai bagian dari kunci komposit
    tabel `cooldowns` -- lihat dokumen desain §4) -- mengganti id kit
    berarti hapus lalu buat ulang, bukan rename di tempat.
    """

    id: str
    metadata: KitMetadata
    items: list = field(default_factory=list)  # list[KitItemData]
    commands: list = field(default_factory=list)  # list[KitCommandEntry]
    created_at: int = field(default_factory=lambda: int(time.time()))
    updated_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            "items": [item.to_dict() for item in self.items],
            "commands": [cmd.to_dict() for cmd in self.commands],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(kit_id: str, data: dict) -> "Kit":
        return Kit(
            id=kit_id,
            metadata=KitMetadata.from_dict(data["metadata"]),
            items=[KitItemData.from_dict(i) for i in data.get("items", [])],
            commands=[
                KitCommandEntry.from_dict(c) for c in data.get("commands", [])
            ],
            created_at=data.get("created_at", int(time.time())),
            updated_at=data.get("updated_at", int(time.time())),
        )
