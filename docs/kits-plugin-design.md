# Desain & Workflow Pengembangan Plugin "Kits" (Endstone)

> **UPDATE (Tahap 4, setelah membaca source code asli Prime BDS di
> https://github.com/PrimeStrat/primebds):** asumsi awal di §1 di
> bawah ini (bahwa dibutuhkan `PrimeBDSPermissionProvider` terpisah
> yang memanggil API/service Prime BDS) **TERNYATA TIDAK BERLAKU**.
> Prime BDS menerapkan permission langsung ke sistem `Permissible`
> bawaan Endstone (`player.addAttachment()` + `setPermission()` +
> `recalculatePermissions()`), sehingga `sender.has_permission(node)`
> standar SUDAH otomatis mencerminkan keputusan Prime BDS tanpa kode
> integrasi khusus apa pun. Implementasi final ada di
> `services/permission_provider.py` (`NativePermissionProvider`
> menjadi satu-satunya provider yang dibutuhkan) dan
> `managers/permission_manager.py`. Bagian §1 & §6.4 di bawah
> dibiarkan apa adanya sebagai jejak proses berpikir awal, bukan
> karena masih berlaku.

> Dokumen ini adalah blueprint teknis sebelum coding dimulai. Referensi API dicek terhadap dokumentasi resmi Endstone (endstone.dev) per Juli 2026 — versi Endstone terbaru sudah punya `ItemMeta` (display name, lore, damage/durability, enchantments), `ItemStack.nbt` untuk akses NBT mentah, `Enchantment` sebagai konstanta, serta `ActionForm` / `ModalForm` / `MessageForm` yang dikirim lewat `Player.send_form()`.

---

## 1. Catatan Penting Sebelum Desain (Asumsi & Batasan API)

Karena keputusan desain sangat bergantung pada kapabilitas nyata Endstone, berikut asumsi yang perlu divalidasi di awal Tahap 1 (buat *spike*/*proof of concept* kecil untuk memverifikasi ini di environment Anda, karena Endstone masih aktif berkembang dan API bisa berubah antar rilis):

| Asumsi | Status | Dampak ke desain |
|---|---|---|
| `ItemStack.get_item_meta()` / `set_item_meta()` tersedia, mendukung `display_name`, `lore`, `damage` (durability), `enchantments` | Terkonfirmasi di changelog & referensi | Jadi dasar `ItemSerializer` |
| `ItemStack.nbt` (getter/setter `CompoundTag`) untuk NBT mentah | Ditambahkan di rilis NBT API terbaru | Fallback untuk data yang tidak dicover `ItemMeta`, termasuk penyimpanan tag custom milik plugin |
| **"Custom Model Data"** ala Java/Paper **tidak punya padanan langsung** di Bedrock | Bedrock tidak mengenal konsep CMD; kustomisasi visual di Bedrock dilakukan lewat resource pack + item name/identifier, bukan lewat metadata angka seperti Java | Fitur ini didesain sebagai **field opsional** (`custom_model_data: Optional[int]`) yang disimpan sebagai NBT tag milik plugin sendiri (bukan field vanilla) — berguna jika suatu saat dipetakan ke resource pack, tapi **tidak menjamin efek visual otomatis**. Ini harus dijelaskan ke admin lewat dokumentasi command. |
| `Player.send_form(ActionForm/ModalForm/MessageForm)` tersedia | Terkonfirmasi | Dasar `GUIManager` |
| Command Bedrock dijalankan sebagai player via `server.dispatch_command(sender, command)` | Pola umum di plugin bergaya Bukkit/Endstone | Dasar `CommandExecutorService` |
| Integrasi **Prime BDS** untuk permission | Belum ada dokumentasi publik API Prime BDS yang bisa saya verifikasi | Didesain via **abstraction layer (`PermissionProvider` interface)**, bukan hardcode — sehingga integrasi nyata tinggal diisi begitu API/service Prime BDS dikonfirmasi (biasanya lewat `server.plugin_manager.get_plugin("PrimeBDS")` lalu memanggil service yang mereka expose, atau lewat file permission mereka). Fallback ke sistem permission native Endstone jika Prime BDS tidak terpasang. |

**Prinsip:** jangan pernah membuat modul inti (KitManager, CooldownManager) bergantung langsung pada Endstone API atau Prime BDS API secara konkret. Semua akses eksternal dibungkus lewat *interface/adapter*, supaya saat API berubah (atau Prime BDS ternyata berbeda dari asumsi), yang diubah cukup 1 file adapter, bukan seluruh plugin.

---

## 2. Prinsip Desain (dan Alasannya)

1. **Layered architecture (Command → Manager → Storage/Model)**
   Command tidak boleh langsung baca/tulis file. Command hanya memanggil Manager. Manager tidak tahu format penyimpanan (YAML/JSON/SQLite) — itu tanggung jawab Storage layer. Ini membuat penyimpanan bisa diganti tanpa menyentuh logic bisnis.

2. **Dependency Injection manual (constructor injection), bukan singleton global**
   Semua Manager menerima dependensinya lewat constructor (`CooldownManager(storage, config)`), bukan lewat `Manager.instance()` global. Alasan: memudahkan unit testing (bisa inject storage palsu/mock) dan menghindari *hidden coupling*.

3. **Satu sumber kebenaran (single source of truth) per data**
   Kit definitions = 1 tempat (KitRepository). Cooldown = 1 tempat (CooldownRepository). Tidak ada cache yang lupa di-invalidate karena akses selalu lewat Manager yang mengatur cache.

4. **Cache in-memory + write-through ke storage**
   Karena kit diklaim berkali-kali per detik (banyak player), *tidak boleh* baca file/DB setiap klaim. Semua data kit & cooldown di-load ke memory saat startup, diakses dari cache, dan setiap perubahan langsung ditulis ke storage secara asinkron/bertahap (write-through). Ini krusial untuk performa server dengan banyak player.

5. **Event-driven untuk hal yang bisa diperluas (extensibility)**
   Saat kit diklaim, plugin memicu custom event (mis. `KitClaimEvent`) sebelum & sesudah proses klaim, supaya plugin lain (atau fitur masa depan seperti logging, economy, quests) bisa "menumpang" tanpa mengubah kode inti.

6. **Command pattern untuk isi kit**
   Baik "item" maupun "console/player command" dalam kit diperlakukan sebagai implementasi dari interface `KitEntry` yang punya method `grant(player)`. Menambah tipe entry baru (mis. "give experience", "teleport") di masa depan tinggal menambah class baru, tanpa mengubah `KitManager`.

7. **Fail-safe & idempotent**
   Kalau server crash di tengah proses klaim kit, cooldown harus tetap konsisten (cooldown dicatat *sebelum* command dieksekusi, bukan sesudah, supaya tidak ada celah dobel klaim saat command lambat/gagal — trade-off didiskusikan di §6.3).

8. **Config terpisah dari data**
   `config.yml` = pengaturan plugin (prefix, format waktu, GUI). `kits.json`/`kits.db` = data kit yang dibuat admin. Tidak dicampur, supaya reset config tidak menghapus data, dan sebaliknya.

---

## 3. Struktur Proyek

```
endstone-kits/
├── pyproject.toml
├── README.md
├── src/
│   └── endstone_kits/
│       ├── __init__.py
│       ├── plugin.py                  # Entry point: class KitsPlugin(Plugin)
│       │
│       ├── commands/                  # Parsing input & output ke player, TIDAK ada business logic
│       │   ├── __init__.py
│       │   ├── kit_command.py         # /kit, /kit list, /kit claim
│       │   └── kit_admin_command.py   # /kit create/edit/delete/cooldown/permission/...
│       │
│       ├── listeners/                 # Event handler Endstone (PlayerJoinEvent, dll)
│       │   ├── __init__.py
│       │   └── player_listener.py     # preload cooldown player saat join, cleanup saat quit
│       │
│       ├── managers/                  # Business logic murni, tidak tahu Endstone API detail
│       │   ├── __init__.py
│       │   ├── kit_manager.py
│       │   ├── cooldown_manager.py
│       │   ├── permission_manager.py
│       │   ├── command_execution_manager.py
│       │   └── gui_manager.py
│       │
│       ├── models/                    # Data class murni (dataclass), tanpa logic berat
│       │   ├── __init__.py
│       │   ├── kit.py                 # Kit, KitMetadata
│       │   ├── kit_item.py            # KitItemData (hasil serialisasi ItemStack)
│       │   ├── kit_command_entry.py
│       │   └── player_cooldown.py
│       │
│       ├── storage/                   # Akses fisik ke file/DB. Tidak ada business logic.
│       │   ├── __init__.py
│       │   ├── base.py                # interface KitRepository, CooldownRepository
│       │   ├── json_kit_repository.py
│       │   └── sqlite_cooldown_repository.py
│       │
│       ├── services/                  # Adapter ke sistem eksternal / Endstone API spesifik
│       │   ├── __init__.py
│       │   ├── item_serializer.py     # ItemStack <-> dict (metadata lengkap)
│       │   ├── placeholder_service.py # {player}, {uuid}, dst.
│       │   └── permission_provider.py # interface + PrimeBDSPermissionProvider + NativePermissionProvider
│       │
│       ├── gui/                       # Pembentukan ActionForm/ModalForm
│       │   ├── __init__.py
│       │   ├── kit_list_form.py
│       │   └── kit_detail_form.py
│       │
│       ├── events/                    # Custom event yang di-fire plugin ini (extensibility hook)
│       │   ├── __init__.py
│       │   └── kit_claim_event.py
│       │
│       ├── utils/                     # Helper murni, stateless
│       │   ├── __init__.py
│       │   ├── time_format.py         # detik -> "1h 20m 5s"
│       │   └── uuid_utils.py
│       │
│       └── config/
│           ├── __init__.py
│           └── config_schema.py       # Validasi & default value config.yml
│
└── resources/
    ├── config.yml
    └── plugin.toml / plugin.yml       # metadata plugin Endstone
```

**Kenapa dipisah seperti ini (bukan 1 file besar):**
- `commands/` hanya parsing argumen & feedback pesan → gampang diaudit typo pesan tanpa takut merusak logic.
- `managers/` adalah "otak" plugin, ditulis agar bisa diuji tanpa server Minecraft menyala sungguhan (unit test dengan mock storage).
- `storage/` mengikuti *Repository Pattern*: manager memanggil `kit_repository.save(kit)`, tidak peduli itu ditulis ke JSON atau SQLite.
- `services/` khusus untuk hal yang menyentuh API eksternal/Endstone secara rinci (item, placeholder, permission) — dipisah dari `managers/` supaya kalau Endstone API berubah, dampaknya terlokalisasi di sini.
- `gui/` dipisah dari `managers/gui_manager.py`: manager mengatur *kapan* & *state*, folder `gui/` mengatur *bentuk visual form*.

---

## 4. Model Data (Domain Model)

```python
# models/kit.py
@dataclass
class KitMetadata:
    display_name: str
    description: str
    icon: str | None          # path/identifier item untuk ikon di GUI
    permission: str | None    # mis. "kits.vip"; None = semua orang boleh
    cooldown_seconds: int     # 0 = tanpa cooldown

@dataclass
class Kit:
    id: str                   # slug unik, immutable, dipakai sebagai primary key
    metadata: KitMetadata
    items: list["KitItemData"]
    commands: list["KitCommandEntry"]
    created_at: datetime
    updated_at: datetime

# models/kit_item.py
@dataclass
class KitItemData:
    slot: int
    type: str                 # item identifier, mis. "minecraft:diamond_sword"
    amount: int
    damage: int | None        # durability terpakai
    display_name: str | None
    lore: list[str]
    enchantments: dict[str, int]   # {"sharpness": 5}
    unbreakable: bool
    custom_model_data: int | None  # lihat catatan §1 (best-effort, disimpan sbg NBT plugin sendiri)
    raw_nbt: str | None       # SNBT string dari ItemStack.nbt, untuk data yang tak tercover field di atas

# models/kit_command_entry.py
@dataclass
class KitCommandEntry:
    template: str              # "give {player} diamond 1"
    run_as: Literal["player"]  # sudah pasti "player" sesuai requirement, tapi dibuat enum utk future "console"

# models/player_cooldown.py
@dataclass
class PlayerCooldown:
    player_uuid: str
    kit_id: str
    last_claimed_at: int        # epoch seconds — hindari drift timezone
```

**Alasan `id` kit berupa slug string, bukan auto-increment int:** command admin (`/kit edit vip`) dan config command lebih natural pakai nama, dan slug stabil dipakai sebagai foreign key di tabel cooldown SQLite tanpa perlu join lookup nama→ID.

**Alasan `last_claimed_at` disimpan sebagai epoch, bukan `datetime` serialized:** menghindari masalah timezone/serialisasi lintas format storage, dan perhitungan sisa cooldown tinggal `now - last_claimed_at`.

---

## 5. Penyimpanan Data (YAML vs JSON vs SQLite)

### Perbandingan

| Kriteria | YAML | JSON | SQLite |
|---|---|---|---|
| Mudah diedit manual oleh admin | ✅ Terbaik (comment, human-friendly) | 🟡 Bisa, tapi tidak ada comment | ❌ Tidak untuk edit manual |
| Performa baca/tulis skala kecil (puluhan kit) | ✅ Baik | ✅ Baik | ✅ Baik (berlebihan tapi tetap cepat) |
| Performa baca/tulis skala besar (ribuan record player×kit) | ❌ Buruk — harus rewrite seluruh file tiap ubah 1 baris | ❌ Sama-sama harus rewrite seluruh file | ✅ Terbaik — update baris tunggal, indexable |
| Query granular (mis. "semua cooldown milik 1 player") | ❌ Harus load semua & filter manual | ❌ Sama | ✅ `WHERE player_uuid = ?` dengan index |
| Concurrency & crash-safety (banyak write bersamaan) | ❌ Rawan corrupt kalau ditulis berbarengan | ❌ Sama | ✅ Transaksi ACID, WAL mode |
| Ketergantungan library | Butuh `PyYAML` | Built-in Python | Built-in Python (`sqlite3`) |

### Rekomendasi: **Hybrid Storage**

- **Kit definitions → JSON** (`kits.json`)
  Alasan: jumlah kit biasanya kecil (puluhan, bukan ribuan), jarang berubah (hanya saat admin create/edit/delete), dan struktur kit itu nested/kompleks (list item dengan banyak field) — JSON lebih natural untuk struktur nested dibanding YAML atau tabel SQL, dan tidak butuh dependency tambahan (`json` built-in). YAML sebenarnya juga cocok dari sisi human-readability, tapi karena isi kit (item + metadata) cukup kompleks dan berpotensi berisi karakter aneh dari lore/NBT, JSON lebih aman terhadap escaping dibanding YAML (YAML rawan parsing error kalau ada karakter spesial di lore).

- **Cooldown per-player-per-kit → SQLite** (`data.db`)
  Alasan: data ini yang paling sering ditulis (setiap kali kit diklaim) dan paling cepat tumbuh (jumlah_player × jumlah_kit baris). Ini butuh:
  - update baris tunggal, bukan rewrite seluruh file → SQLite unggul jauh.
  - query "ambil semua cooldown milik player X saat dia join" → `SELECT * WHERE player_uuid=?` dengan index, O(log n) bukan O(n) seperti scan file JSON/YAML.
  - aman dari corrupt saat banyak player klaim kit bersamaan (SQLite transaksi atomik + WAL mode `PRAGMA journal_mode=WAL`).

- **Config (`config.yml`) → YAML**
  Alasan: config diedit manual oleh admin di teks editor, butuh comment penjelasan tiap opsi — ini keunggulan YAML dibanding JSON.

**Skema tabel `cooldowns`:**
```sql
CREATE TABLE cooldowns (
    player_uuid TEXT NOT NULL,
    kit_id      TEXT NOT NULL,
    last_claimed_at INTEGER NOT NULL,
    PRIMARY KEY (player_uuid, kit_id)
);
CREATE INDEX idx_cooldowns_player ON cooldowns(player_uuid);
```

Composite primary key `(player_uuid, kit_id)` otomatis jadi index, mengcover requirement "cooldown per-player per-kit, tetap tersimpan walau restart".

---

## 6. Arsitektur & Tanggung Jawab Manager

```
Player/Admin
   │
   ▼
CommandRouter (commands/)
   │  (parsing argumen, permission-check dasar, feedback pesan)
   ▼
Managers (business logic)
   ├── KitManager           -> CRUD kit, validasi input, cache kit di memory
   ├── CooldownManager       -> cek/set cooldown, format sisa waktu
   ├── PermissionManager     -> delegasi ke PermissionProvider (Prime BDS / native)
   ├── CommandExecutionManager -> render placeholder & dispatch command as player
   └── GUIManager            -> compose ActionForm/ModalForm, handle callback
   │
   ▼
Storage/Services (I/O nyata)
   ├── KitRepository (JSON)
   ├── CooldownRepository (SQLite)
   ├── ItemSerializer (Endstone ItemStack <-> KitItemData)
   └── PermissionProvider (Prime BDS API / Endstone native permission)
```

### 6.1 `KitManager`
- Tanggung jawab: create/edit/delete kit, validasi (nama unik, kit ada/tidak), cache seluruh kit di `dict[str, Kit]` in-memory saat plugin enable.
- Saat `create_kit(admin, name)`: ambil isi inventory admin lewat `admin.inventory`, loop tiap slot, delegasikan ke `ItemSerializer.serialize(item_stack)` per slot (tidak menaruh logic serialisasi item di sini — Single Responsibility).
- Semua mutasi (create/edit/delete) langsung `kit_repository.save_all(kits)` (write-through) agar data tidak hilang saat crash mendadak.

### 6.2 `CooldownManager`
- `can_claim(player_uuid, kit) -> bool`
- `get_remaining(player_uuid, kit) -> int` (detik)
- `set_claimed(player_uuid, kit_id)` → tulis ke cache + `cooldown_repository.upsert(...)`
- Cache: `dict[(player_uuid, kit_id), int]` di memory, di-load penuh saat plugin start (atau lazy-load per player saat join, lebih hemat memori jika player banyak & histori kit banyak — pilih **lazy-load per-player saat join, dibuang saat player quit**, supaya memory tidak membengkak di server besar).

### 6.3 Keputusan desain penting: kapan cooldown "dimulai"?
Dua opsi:
- **(A) Cooldown dicatat sebelum command/item diberikan.** Trade-off: kalau pemberian item gagal di tengah jalan (mis. server lag), player tetap kena cooldown padahal tidak dapat kit penuh.
- **(B) Cooldown dicatat sesudah semua item & command sukses diberikan.** Trade-off: kalau player klik tombol GUI berkali-kali sangat cepat (double click) sebelum proses pertama selesai, berisiko dapat kit dobel.

**Rekomendasi:** gunakan pola *reserve-then-commit*: tandai kit "sedang diproses" untuk player tsb secara in-memory (lock singkat) sebelum mulai memberi item, cooldown dicatat **setelah proses grant selesai** (opsi B), tapi lock in-memory mencegah race condition dobel-klik. Ini menghindari kedua trade-off di atas sekaligus, dan hanya butuh `set[tuple[uuid,kit_id]]` sederhana sebagai in-progress lock.

### 6.4 `PermissionManager` & `PermissionProvider`
```python
class PermissionProvider(Protocol):
    def has_permission(self, player: Player, permission: str) -> bool: ...

class NativePermissionProvider(PermissionProvider):
    """Fallback: pakai player.has_permission() bawaan Endstone."""

class PrimeBDSPermissionProvider(PermissionProvider):
    """Delegasi ke Prime BDS. Diisi setelah API Prime BDS diverifikasi (Tahap 4)."""
```
`PermissionManager` dipilih otomatis: cek apakah plugin "PrimeBDS" terpasang di `server.plugin_manager`; jika ya pakai `PrimeBDSPermissionProvider`, jika tidak fallback ke `NativePermissionProvider`. **Alasan:** plugin ini tidak boleh gagal total (hard-crash) hanya karena Prime BDS belum/tidak terpasang di server tertentu — penting untuk *portability* & *maintainability*.

### 6.5 `CommandExecutionManager`
- `execute(player, template: str)`:
  1. Replace placeholder: `{player}` → `player.name`, `{uuid}` → `str(player.unique_id)`.
  2. Dispatch: `server.dispatch_command(player, rendered)` — dijalankan **sebagai player**, bukan console, sesuai requirement.
- Placeholder logic ditaruh di `services/placeholder_service.py` (bukan di manager) supaya mudah menambah placeholder baru (`{kit_id}`, `{server_name}`, dll) tanpa menyentuh `CommandExecutionManager`.

### 6.6 `GUIManager`
- `open_kit_list(player)` → build `ActionForm` dari seluruh kit yang **permission-nya dimiliki player** (filter dulu lewat `PermissionManager`), tiap tombol menampilkan nama kit + status cooldown (mis. "VIP Kit (Ready)" / "VIP Kit (12m left)").
- `open_kit_detail(player, kit)` → `ActionForm`/`MessageForm` menampilkan deskripsi, permission, isi kit ringkas, tombol "Claim" (disabled/hint kalau masih cooldown — Bedrock form tidak mendukung disable tombol asli, jadi tombol tetap ada tapi callback menampilkan pesan cooldown, bukan menyembunyikan tombol, supaya tidak membingungkan player).

---

## 7. Command & Permission

| Command | Fungsi | Permission |
|---|---|---|
| `/kit` | Buka GUI daftar kit (atau list teks jika GUI dimatikan) | `kits.use` |
| `/kit list` | Tampilkan semua kit yang bisa diakses player | `kits.use` |
| `/kit claim <kit>` | Klaim kit tertentu | `kits.use` + permission spesifik kit (mis. `kits.vip`) |
| `/kit info <kit>` | Info detail 1 kit | `kits.use` |
| `/kit create <kit>` | Buat kit baru dari inventory | `kits.admin.create` |
| `/kit edit <kit>` | Update isi kit dari inventory saat ini | `kits.admin.edit` |
| `/kit delete <kit>` | Hapus kit | `kits.admin.delete` |
| `/kit cooldown <kit> <detik>` | Atur cooldown kit | `kits.admin.cooldown` |
| `/kit permission <kit> <node>` | Atur permission node kit | `kits.admin.permission` |
| `/kit addcommand <kit> <command...>` | Tambah command ke kit | `kits.admin.command` |
| `/kit removecommand <kit> <index>` | Hapus command dari kit | `kits.admin.command` |
| `/kit reload` | Reload config & data dari disk | `kits.admin.reload` |

**Alasan setiap sub-permission dipisah** (bukan cukup `kits.admin`): supaya server owner bisa memberi staff-tier tertentu izin edit cooldown saja tanpa bisa hapus kit, sesuai prinsip *least privilege* — juga selaras dengan requirement plugin harus terintegrasi rapi dengan sistem permission (Prime BDS) yang biasanya granular per-node.

---

## 8. Konfigurasi (`config.yml`)

```yaml
# Prefix untuk semua pesan plugin
prefix: "&8[&bKits&8] &r"

messages:
  no_permission: "&cKamu tidak punya izin untuk kit ini."
  cooldown_active: "&eTunggu {time} lagi sebelum klaim ulang."
  kit_claimed: "&aKamu berhasil klaim kit {kit}."
  kit_not_found: "&cKit '{kit}' tidak ditemukan."
  kit_created: "&aKit '{kit}' berhasil dibuat."

cooldown:
  time_format: "long"   # "long" -> "1 jam 20 menit", "short" -> "1j 20m"

gui:
  enabled: true
  title: "Daftar Kit"
  show_permission_in_lore: true
  show_time_remaining: true

storage:
  kits_file: "kits.json"
  database_file: "data.db"
  sqlite_wal_mode: true

permissions:
  provider: "auto"   # "auto" | "prime_bds" | "native"
```

**Alasan `permissions.provider: auto`:** admin server tidak perlu tahu detail implementasi; plugin otomatis deteksi Prime BDS, tapi opsi override manual disediakan untuk debugging/kasus edge.

---

## 9. Roadmap Implementasi (Tahapan)

**Tahap 1 — Fondasi**
- Setup `pyproject.toml`, struktur folder, `plugin.py` entry point kosong yang bisa di-load Endstone.
- `config_schema.py` + load/generate `config.yml` default.
- `storage/base.py` (interface repository) + implementasi JSON kit repository & SQLite cooldown repository (masih dengan data dummy, belum terhubung ke command).
- Deliverable: plugin bisa di-load server, buat file config & db kosong, tanpa error.

**Tahap 2 — Sistem Kit & Serialisasi Item**
- `models/kit.py`, `models/kit_item.py`.
- `services/item_serializer.py`: uji coba serialisasi tiap jenis item (enchant, lore, custom name, damage) dari inventory sungguhan → dict → kembali ke ItemStack, validasi tidak ada data hilang (round-trip test manual).
- `managers/kit_manager.py`: create/edit/delete + cache in-memory.
- Command `/kit create`, `/kit edit`, `/kit delete`, `/kit info`, `/kit list` (versi teks dulu, tanpa GUI).
- Deliverable: admin bisa buat kit dari inventory dan lihat isinya lewat command teks.

**Tahap 3 — Cooldown**
- `models/player_cooldown.py`, `storage/sqlite_cooldown_repository.py` (skema final).
- `managers/cooldown_manager.py` + lazy-load per player saat `PlayerJoinEvent`, cleanup saat `PlayerQuitEvent`.
- `/kit claim` versi dasar (belum permission, belum command execution) untuk uji cooldown murni.
- Deliverable: klaim kit dibatasi cooldown, bertahan setelah restart server (uji manual: klaim → restart → cek cooldown tetap ada).

**Tahap 4 — Permission (Prime BDS)**
- Verifikasi API nyata Prime BDS (cek plugin.jar/py mereka atau minta dokumentasi ke pembuatnya) — ini **wajib** dilakukan sebelum implementasi `PrimeBDSPermissionProvider` sungguhan.
- `services/permission_provider.py`: interface + `NativePermissionProvider` (selesai duluan, tidak butuh dependensi eksternal) + `PrimeBDSPermissionProvider` (setelah API dikonfirmasi).
- `managers/permission_manager.py`: auto-detect provider.
- Integrasi permission ke `/kit claim` dan filter `/kit list`.
- Deliverable: player tanpa `kits.vip` tidak bisa klaim kit VIP; test dengan & tanpa Prime BDS terpasang.

**Tahap 5 — Command Execution**
- `services/placeholder_service.py` (`{player}`, `{uuid}`, dibuat extensible untuk placeholder baru).
- `managers/command_execution_manager.py`, integrasi ke `KitManager.grant_kit()` (item + command dieksekusi dalam satu alur "grant").
- `/kit addcommand`, `/kit removecommand`.
- Deliverable: klaim kit memberi item **dan** menjalankan command sebagai player dengan placeholder terisi benar.

**Tahap 6 — GUI**
- `gui/kit_list_form.py`, `gui/kit_detail_form.py`, `managers/gui_manager.py`.
- `/kit` tanpa argumen membuka form kalau `gui.enabled: true` di config, fallback ke list teks kalau `false`.
- Deliverable: player buka `/kit`, lihat daftar kit dengan status cooldown, klik untuk klaim.

**Tahap 7 — Testing, Optimisasi, Dokumentasi**
- Uji beban: simulasi banyak player klaim kit bersamaan (concurrency test pada SQLite WAL).
- Review memory: pastikan cache cooldown ter-cleanup saat player quit (tidak ada memory leak).
- Tulis dokumentasi command & permission untuk admin (README).
- Code review pass: cek tidak ada logic bisnis nyasar ke `commands/` atau I/O nyasar ke `managers/`.

---

## 10. Ringkasan Alasan Desain Kunci

| Keputusan | Alasan Utama |
|---|---|
| Layered architecture (command/manager/storage terpisah) | Ganti storage atau ubah pesan command tidak merembet ke logic bisnis |
| Hybrid storage (JSON kit + SQLite cooldown) | Kit = kecil & jarang berubah (cocok JSON), cooldown = besar & sering berubah (butuh SQLite untuk performa & crash-safety) |
| Cache in-memory + write-through | Server dengan banyak player tidak boleh I/O disk di setiap klaim kit |
| `PermissionProvider` abstraction | Prime BDS API belum terverifikasi penuh; hindari hard dependency yang bisa merusak seluruh plugin jika API berbeda dari asumsi |
| Command pattern untuk isi kit (item vs command sebagai `KitEntry`) | Menambah tipe entry baru di masa depan tidak mengubah kode inti |
| Reserve-then-commit untuk cooldown | Cegah dobel klaim dari double-click GUI tanpa menghukum player saat proses grant gagal di tengah jalan |
| Custom Model Data sebagai field best-effort | Bedrock tidak punya konsep CMD asli seperti Java; field disediakan untuk future-proofing, bukan jaminan visual |

---

**Langkah selanjutnya:** jika desain ini disetujui, implementasi dimulai dari **Tahap 1** sesuai roadmap di atas — tiap tahap diberikan sebagai unit kerja terpisah supaya bisa direview & diuji sebelum lanjut ke tahap berikutnya, bukan langsung 1 dump source code penuh.
