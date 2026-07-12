"""
Bentuk visual form daftar kit (ActionForm).

Folder `gui/` HANYA mengatur bentuk visual -- data (kit mana yang
boleh dilihat, teks status cooldown) sudah disiapkan sepenuhnya oleh
`managers/gui_manager.py` sebelum dikirim ke sini. File ini tidak
memanggil manager/storage apa pun.
"""
from __future__ import annotations

from typing import Callable, List, Tuple

from endstone.form import ActionForm, Button


def build_kit_list_form(
    entries: List[Tuple[object, str]],
    title: str,
    on_select: Callable[[object, str], None],
) -> ActionForm:
    """`entries`: list of (Kit, status_text) yang sudah difilter &
    disiapkan oleh GUIManager. `on_select(player, kit_id)` dipanggil
    saat salah satu kit diklik."""
    buttons = []
    for kit, status_text in entries:
        label = f"{kit.metadata.display_name}\n{status_text}"
        # `kit_id=kit.id` sebagai default argument WAJIB di sini --
        # tanpa ini, closure Python akan menangkap variabel `kit` dari
        # iterasi TERAKHIR loop untuk SEMUA tombol (classic late
        # binding bug), bukan kit yang sesuai tombolnya masing-masing.
        buttons.append(
            Button(
                text=label,
                on_click=lambda player, kit_id=kit.id: on_select(player, kit_id),
            )
        )

    return ActionForm(
        title=title,
        content="Pilih kit yang ingin dilihat/diklaim:",
        buttons=buttons,
    )
