from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from endstone_kits.storage.base import KitRepository


class JsonKitRepository(KitRepository):
    """Implementasi `KitRepository` berbasis file JSON tunggal
    (`kits.json`).

    Kenapa JSON (bukan SQLite) untuk kit -- lihat dokumen desain §5:
    jumlah kit kecil (puluhan, bukan ribuan) dan jarang berubah (hanya
    saat admin create/edit/delete), sedangkan strukturnya nested
    (kit -> list item -> enchantments/lore/dll) yang lebih natural
    direpresentasikan sebagai JSON dibanding tabel relasional atau
    YAML (YAML rawan gagal parse kalau lore/nama item mengandung
    karakter spesial).
    """

    def __init__(self, path: Path):
        self._path = Path(path)
        if not self._path.exists():
            self.save_all({"kits": {}})

    def load_all(self) -> dict:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # File belum ada atau corrupt -> mulai dari struktur kosong
            # daripada meng-crash seluruh plugin saat startup.
            data = {"kits": {}}
        if not isinstance(data, dict):
            data = {"kits": {}}
        data.setdefault("kits", {})
        return data

    def save_all(self, data: dict) -> None:
        """Atomic write: tulis ke file sementara di folder yang sama,
        lalu `os.replace` (rename atomik di level filesystem).

        Kenapa penting: kalau proses ke-interrupt (server crash, kill
        paksa) tepat saat menulis, tanpa pola ini `kits.json` bisa
        berakhir setengah tertulis dan tidak valid lagi sebagai JSON
        -- membuat seluruh data kit hilang saat restart berikutnya.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._path.parent), prefix=".kits_", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self._path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
