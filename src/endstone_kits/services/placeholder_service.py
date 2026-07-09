"""
Placeholder untuk template command isi kit (mis. "give {player} diamond 1").

Ini SATU-SATUNYA tempat yang tahu placeholder apa saja yang didukung.
Menambah placeholder baru (mis. "{kit_id}", "{server_name}") di masa
depan cukup menambah 1 baris di `render_placeholders()` -- tidak perlu
mengubah `CommandExecutionManager` atau tempat lain.
"""
from __future__ import annotations


def render_placeholders(template: str, player) -> str:
    """`player` cukup punya atribut `.name` dan `.unique_id` -- tidak
    diketik ketat ke `endstone.Player` supaya fungsi ini tetap mudah
    diuji dengan objek player palsu (lihat unit test)."""
    replacements = {
        "{player}": player.name,
        "{uuid}": str(player.unique_id),
    }
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result
