"""
Bentuk visual form detail 1 kit (ActionForm dengan tombol Klaim &
Kembali). Sama seperti `kit_list_form.py`, file ini HANYA mengatur
tampilan -- tidak memanggil manager/storage apa pun.
"""
from __future__ import annotations

from typing import Callable

from endstone.form import ActionForm, Button


def build_kit_detail_form(
    kit,
    status_text: str,
    on_claim: Callable[[object], None],
    on_back: Callable[[object], None],
) -> ActionForm:
    meta = kit.metadata
    cooldown_line = (
        "Cooldown  : tidak berlaku (sekali pakai)"
        if meta.one_time
        else f"Cooldown  : {meta.cooldown_seconds} detik"
    )
    lines = [
        f"Deskripsi : {meta.description or '-'}",
        f"Permission: {meta.permission or '(tidak ada)'}",
        cooldown_line,
        f"Status    : {status_text}",
        f"Jumlah item: {len(kit.items)}",
    ]

    return ActionForm(
        title=meta.display_name,
        content="\n".join(lines),
        buttons=[
            Button(text="Klaim", on_click=lambda player: on_claim(player)),
            Button(text="Kembali", on_click=lambda player: on_back(player)),
        ],
    )
