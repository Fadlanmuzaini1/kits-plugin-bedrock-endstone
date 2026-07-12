from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from endstone_kits.storage.base import CooldownRepository


class SqliteCooldownRepository(CooldownRepository):
    """Implementasi `CooldownRepository` berbasis SQLite.

    Kenapa SQLite (bukan JSON/YAML) untuk cooldown -- lihat dokumen
    desain §5: data ini yang paling sering ditulis (setiap kali kit
    diklaim) dan paling cepat tumbuh (baris = jumlah_player x
    jumlah_kit). SQLite memungkinkan:
      - update baris tunggal via UPSERT, bukan rewrite seluruh file.
      - query cepat "semua cooldown milik player X" lewat index.
      - transaksi atomik, aman dari corrupt saat banyak player klaim
        kit hampir bersamaan.
    """

    def __init__(self, path: Path, wal_mode: bool = True):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # check_same_thread=False: command/event Endstone berpotensi
        # dipanggil dari thread yang berbeda dari thread yang membuat
        # koneksi ini. Keamanan akses paralel dijamin secara eksplisit
        # lewat `self._lock` di bawah, bukan mengandalkan default
        # sqlite3 (yang justru akan melempar error tanpa opsi ini).
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._lock = threading.Lock()

        if wal_mode:
            # WAL (Write-Ahead Logging): pembaca tidak memblokir
            # penulis dan sebaliknya -- penting saat banyak player
            # klaim kit di waktu yang berdekatan.
            self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cooldowns (
                    player_uuid     TEXT NOT NULL,
                    kit_id          TEXT NOT NULL,
                    last_claimed_at INTEGER NOT NULL,
                    PRIMARY KEY (player_uuid, kit_id)
                )
                """
            )
            # Composite primary key di atas sudah otomatis membuat index,
            # tapi index eksplisit berikut mempercepat query
            # "semua cooldown milik 1 player" (dipakai saat player join)
            # tanpa perlu menyertakan kit_id di kondisi WHERE.
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cooldowns_player "
                "ON cooldowns(player_uuid)"
            )
            self._conn.commit()

    def get_all_for_player(self, player_uuid: str) -> dict[str, int]:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT kit_id, last_claimed_at FROM cooldowns WHERE player_uuid = ?",
                (player_uuid,),
            )
            rows = cursor.fetchall()
        return {kit_id: last_claimed_at for kit_id, last_claimed_at in rows}

    def upsert(self, player_uuid: str, kit_id: str, last_claimed_at: int) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO cooldowns (player_uuid, kit_id, last_claimed_at)
                VALUES (?, ?, ?)
                ON CONFLICT(player_uuid, kit_id)
                DO UPDATE SET last_claimed_at = excluded.last_claimed_at
                """,
                (player_uuid, kit_id, last_claimed_at),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
