# Progres Plugin Kits — Tahap 2 & Tahap 3

> Status proyek: `endstone-kits`, versi kode di `plugin.py` = `0.3.0`.
> Dokumen ini merangkum apa yang sudah dibangun, sudah diuji, dan
> batasan yang **disengaja** (belum dikerjakan karena memang jadwalnya
> di tahap berikutnya) — bukan bug.

---

## Tahap 2 — Sistem Kit & Serialisasi Item

### Tujuan
Admin bisa membuat kit dari isi inventory-nya sendiri, lengkap dengan
metadata item (nama custom, lore, enchantment, durability), lalu
mengedit/menghapusnya.

### File yang ditambahkan

| File | Isi |
|---|---|
| `models/kit_item.py` | `KitItemData` — 1 item di dalam kit (slot, type, amount, display_name, lore, damage, unbreakable, enchantments, custom_model_data, raw_nbt) + `to_dict()`/`from_dict()`. |
| `models/kit_command_entry.py` | `KitCommandEntry` — 1 baris command isi kit (template, run_as). Baru jadi model data; **belum dieksekusi** (itu Tahap 5). |
| `models/kit.py` | `KitMetadata` (nama, deskripsi, ikon, permission, cooldown) & `Kit` (id + metadata + items + commands + timestamp). |
| `services/item_serializer.py` | `ItemSerializer` — satu-satunya kode yang tahu detail `ItemStack`/`ItemMeta` Endstone. `serialize()`: ItemStack → `KitItemData`. `deserialize()`: `KitItemData` → ItemStack baru. |
| `managers/kit_manager.py` | `KitManager` — CRUD kit: `create_from_inventory`, `edit_items_from_inventory`, `delete`, `set_cooldown`, `set_permission`, `list_all`, `get`, `reload`. Cache in-memory + **write-through** (setiap mutasi langsung ditulis ke `kits.json`). |
| `commands/kit_command.py` | Sub-command player: `list`, `info`. |
| `commands/kit_admin_command.py` | Sub-command admin: `create`, `edit`, `delete`, `cooldown`, `permission`. Semua yang butuh inventory (`create`, `edit`) memvalidasi sender adalah `Player`, bukan console. |

### Command yang aktif sejak Tahap 2
```
/kit list
/kit info <id>
/kit create <id> [nama tampilan]
/kit edit <id>
/kit delete <id>
/kit cooldown <id> <detik>
/kit permission <id> <node|none>
/kit reload
```

### Detail teknis penting

- **`ItemStack.item_meta` mengembalikan SALINAN**, bukan referensi —
  perubahan harus di-*apply* balik lewat `set_item_meta()`. Sudah
  ditangani dengan benar di `ItemSerializer`.
- **Enchantment**: `ItemMeta.enchants` berisi `dict[Enchantment, int]`
  (key berupa objek, bukan string) → dikonversi ke string id lewat
  `enchant.id` saat serialize, dan `add_enchant(id, level, force=True)`
  saat deserialize. `force=True` supaya level enchant custom admin
  (mis. Sharpness 10) tidak ditolak validasi vanilla.
- **Custom Model Data**: Bedrock **tidak** punya konsep ini seperti
  Java/Paper. Field `custom_model_data` disediakan di model data tapi
  selalu `None` dari hasil serialize — best-effort/future-proofing,
  bukan jaminan efek visual.
- **`raw_nbt`**: disimpan sebagai string SNBT HANYA untuk referensi
  admin/debug. **Tidak dipakai lagi saat deserialize** — belum ada
  cara aman terverifikasi untuk parse SNBT kembali jadi `CompoundTag`
  tanpa risiko merusak item. Metadata fungsional (nama, lore, damage,
  enchant, unbreakable) sudah 100% tercakup via `ItemMeta`.
- **Enchant tidak valid** (id salah ketik/tidak cocok tipe item) di-
  *skip* satu per satu, tidak menggagalkan seluruh proses pemberian
  kit.

### Yang sudah diuji
- Round-trip penuh: `serialize → to_dict (JSON) → from_dict →
  deserialize` menjaga nama custom, lore, durability, unbreakable, dan
  2 enchantment berbeda — semua identik dengan item asli.
- `KitManager`: create (dengan cek duplikat ditolak), edit item tanpa
  mengubah metadata, delete idempotent, `set_cooldown`/`set_permission`,
  write-through ke storage, `reload()`.
- Import penuh seluruh modul memakai package `endstone` asli (v0.11.5)
  — bukan cuma stub buatan sendiri.

### Batasan yang disengaja
- `/kit list` & `/kit info` belum memfilter berdasarkan permission
  player (semua kit terlihat oleh siapa saja dengan `kits.use`) —
  menyusul Tahap 4.
- Command isi kit (`KitCommandEntry`) baru jadi struktur data, belum
  ada eksekusinya — Tahap 5.

---

## Tahap 3 — Cooldown

### Tujuan
Kit tidak bisa diklaim berulang-ulang tanpa jeda; cooldown diatur
per-kit, dihitung per-player, dan tetap tersimpan walau server restart.

### File yang ditambahkan

| File | Isi |
|---|---|
| `models/player_cooldown.py` | `PlayerCooldown` — dataclass dokumentasi 1 baris cooldown (player_uuid, kit_id, last_claimed_at). Dipakai untuk kejelasan struktur data; `CooldownManager` sendiri pakai dict polos demi performa. |
| `utils/time_format.py` | `format_duration(seconds, style)` — ubah detik jadi teks `"1 jam 20 menit 5 detik"` (style `"long"`) atau `"1j 20m 5d"` (style `"short"`). |
| `managers/cooldown_manager.py` | `CooldownManager` — inti Tahap 3 (detail di bawah). |
| `listeners/player_listener.py` | `PlayerListener` — `@event_handler` untuk `PlayerJoinEvent` (lazy-load cache) & `PlayerQuitEvent` (buang cache). |
| `managers/kit_manager.py` (update) | Tambahan method `grant_items_to(kit_id, player)` — beri semua item kit ke inventory player, kembalikan leftover kalau inventory penuh. |
| `commands/kit_command.py` (update) | Tambahan sub-command `claim`. |

### Command yang aktif sejak Tahap 3
```
/kit claim <id>
```

### Cara kerja `CooldownManager`

1. **Cache in-memory** `(player_uuid, kit_id) -> epoch_detik`, di-lazy-
   load per player saat **join** (bukan semua player sekaligus saat
   plugin start), dan dibuang saat **quit** — supaya memory tidak
   membengkak di server dengan banyak player & histori kit banyak.
2. **`get_remaining_seconds()`** — hitung sisa cooldown dari cache;
   kalau `cooldown_seconds <= 0` selalu `0` (tanpa cooldown).
3. **Reserve-then-commit** (`try_reserve()` / `release()` /
   `mark_claimed()`) — pola untuk mencegah dobel klaim dari
   double-klik command/GUI:
   - `try_reserve()` mengunci kombinasi (player, kit) sebelum proses
     pemberian item dimulai; kalau sudah terkunci (proses sebelumnya
     belum selesai), permintaan baru ditolak.
   - Item baru diberikan **setelah** lock berhasil didapat.
   - Cooldown baru dicatat (`mark_claimed`) **setelah** pemberian item
     selesai sukses — kalau proses gagal di tengah jalan, player tidak
     dikenai cooldown untuk kit yang gagal diberikan.
   - `release()` dipanggil di blok `finally`, jadi lock selalu terlepas
     walau terjadi error.
4. **Persistensi**: setiap `mark_claimed()` langsung `UPSERT` ke tabel
   SQLite `cooldowns` (bukan hanya cache) — inilah yang membuat
   cooldown bertahan lintas restart.

### Alur `/kit claim <id>`
```
cek kit ada?
  → tidak: pesan "kit tidak ditemukan"
cek sisa cooldown (get_remaining_seconds)
  → > 0: pesan "tunggu {time} lagi"
try_reserve()
  → gagal (sedang diproses): pesan "klaim sebelumnya masih diproses"
  → berhasil:
      grant_items_to() (beri item, catat leftover kalau inventory penuh)
      finally: release()
      mark_claimed() (HANYA kalau grant tidak melempar exception)
      pesan "berhasil klaim kit {kit}"
      (kalau ada leftover) pesan "inventory penuh, N stack hilang"
```

### Yang sudah diuji
- `CooldownManager` (mock repository, tanpa `endstone`): belum pernah
  klaim → boleh; `cooldown_seconds=0` → selalu boleh; reserve kedua
  untuk kombinasi sama ditolak; cooldown tercatat mendekati nilai
  penuh; **simulasi restart** (buat instance baru dari repo yang sama)
  → cooldown tetap ada; `unload_player` hanya buang cache (bukan data
  di storage); cooldown per-kit dihitung terpisah (multi-kit).
- `SqliteCooldownRepository` asli (bukan mock): upsert per
  player/kit, overwrite (bukan duplikat baris) untuk kombinasi yang
  sama, **data bertahan setelah koneksi ditutup & dibuka ulang**.
- `format_duration`: semua kombinasi detik/menit/jam/hari, style
  `long` & `short`.
- Import penuh seluruh modul (termasuk `listeners/player_listener.py`
  yang memakai `endstone.event`) dengan package `endstone` asli v0.11.5.

### Batasan yang disengaja
- **Belum ada pengecekan permission per-kit** saat klaim — siapa pun
  dengan `kits.use` bisa klaim kit apa pun (VIP, MVP, staff, dst.)
  asal cooldown-nya sudah habis. Ini adalah fokus **Tahap 4**
  (`PermissionManager` + integrasi Prime BDS).
- **Command isi kit belum dieksekusi** saat klaim (baru item saja) —
  fokus **Tahap 5**.
- Kalau ada beberapa server/instance berbeda berbagi 1 file
  `cooldowns.db` secara bersamaan (bukan skenario umum single-server),
  belum ada penanganan khusus multi-proses selain locking bawaan
  SQLite/WAL.

---

## Ringkasan Command Saat Ini (akhir Tahap 3)

| Command | Sejak Tahap | Permission |
|---|---|---|
| `/kit` | 1 | `kits.use` |
| `/kit list` | 2 | `kits.use` |
| `/kit info <id>` | 2 | `kits.use` |
| `/kit claim <id>` | 3 | `kits.use` |
| `/kit reload` | 1 | `kits.admin.reload` |
| `/kit create <id> [nama]` | 2 | `kits.admin.create` |
| `/kit edit <id>` | 2 | `kits.admin.edit` |
| `/kit delete <id>` | 2 | `kits.admin.delete` |
| `/kit cooldown <id> <detik>` | 2 | `kits.admin.cooldown` |
| `/kit permission <id> <node|none>` | 2 | `kits.admin.permission` |

## Langkah Berikutnya

**Tahap 4 — Permission (Prime BDS)**: verifikasi API nyata Prime BDS,
implementasi `PrimeBDSPermissionProvider` (dengan fallback otomatis ke
permission native Endstone kalau Prime BDS tidak terpasang), lalu
integrasikan pengecekan permission per-kit ke `/kit claim` dan filter
`/kit list`.
