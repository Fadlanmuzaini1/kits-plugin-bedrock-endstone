#### (Choose your language below / Pilih bahasa dibawah)
[![English](https://img.shields.io/badge/Language-English-blue)](README.en.md)
[![Bahasa Indonesia](https://img.shields.io/badge/Language-Indonesia-green)](README.md)
---

# Endstone Kits

Plugin sistem **Kits** untuk server Minecraft Bedrock berbasis
[Endstone](https://endstone.dev). Admin membuat kit langsung dari isi
inventory mereka (lengkap dengan enchant, lore, nama custom,
durability), player mengklaimnya lewat command atau GUI, dengan
cooldown per-player-per-kit yang tersimpan permanen dan permission
per-kit yang terintegrasi otomatis dengan sistem permission server
(termasuk [Prime BDS](https://github.com/PrimeStrat/primebds)).

## Fitur Utama

- **Buat kit dari inventory** — isi kit (item + metadata lengkap)
  diambil langsung dari inventory admin saat membuat kit lewat command,
  tidak perlu menulis konfigurasi item manual.
- **Metadata item lengkap** — nama custom, lore, enchantment,
  durability (damage), dan status unbreakable semuanya tersimpan &
  dipulihkan utuh saat kit diklaim.
- **Cooldown per-player per-kit** — diatur per kit, dihitung terpisah
  untuk tiap player, dan **tetap tersimpan walau server restart**
  (disimpan di SQLite, bukan hanya di memory).
- **Kit sekali pakai (one-time)** — opsi supaya sebuah kit hanya bisa
  diklaim SATU KALI oleh tiap player, selamanya (cocok untuk kit
  starter/pendaftaran), terlepas dari pengaturan cooldown biasa.
- **Permission otomatis** — setiap kit baru otomatis dapat permission
  `kits.<nama_kit>`, bisa ditimpa manual kapan saja. Terintegrasi
  dengan Prime BDS tanpa konfigurasi tambahan apa pun (lihat
  [Integrasi Permission](#integrasi-permission-prime-bds--server-lain)).
- **Command isi kit** — kit bisa menjalankan command tambahan saat
  diklaim (mis. efek, pesan, teleport), dieksekusi **sebagai player**
  yang mengklaim ATAU **sebagai server/console** (dipilih per command
  saat `/kit addcommand`), dengan placeholder `{player}` & `{uuid}`.
- **GUI & command teks** — `/kit` tanpa argumen membuka form pemilihan
  kit di client Bedrock (bisa dimatikan lewat config), atau tetap bisa
  dipakai murni lewat command teks.
- **Multi-kit** — satu player bisa punya akses ke banyak kit sekaligus,
  cooldown masing-masing dihitung independen.

## Instalasi

1. Build wheel plugin (butuh Python 3.10+ dan package `endstone`
   ter-install di environment yang sama dengan server):
   ```bash
   pip install -e .
   ```
   atau build wheel biasa (`pip install build && python -m build`) lalu
   pasang hasilnya sesuai cara Endstone memuat plugin Python di server
   Anda.
2. Jalankan/restart server. Plugin otomatis membuat:
   - `config.toml` — file konfigurasi (lihat [Konfigurasi](#konfigurasi)).
   - `kits.json` — data seluruh kit yang dibuat admin.
   - `cooldowns.db` — data cooldown per-player per-kit (SQLite).

   Ketiganya dibuat di folder data plugin (biasanya
   `plugins/Kits/` atau serupa, tergantung konfigurasi server Anda).

## Command

| Command | Deskripsi | Permission |
|---|---|---|
| `/kit` | Buka GUI pemilihan kit (kalau `gui.enabled: true` & sender player), atau tampilkan daftar teks | `kits.use` |
| `/kit list` | Tampilkan daftar kit yang bisa diakses (sudah difilter permission) | `kits.use` |
| `/kit info <id>` | Info detail kit: nama, deskripsi, permission, cooldown, jumlah item & command | `kits.use` |
| `/kit claim <id>` | Klaim kit (cek permission & cooldown, beri item, jalankan command isi kit) | `kits.use` |
| `/kit reload` | Reload `config.toml` & `kits.json` dari disk | `kits.admin.reload` |
| `/kit create <id> <cooldown_detik> [nama tampilan]` | Buat kit baru dari inventory sender. Permission otomatis `kits.<id>` | `kits.admin.create` |
| `/kit edit <id>` | Ganti isi item kit dengan inventory sender saat ini (metadata tidak berubah) | `kits.admin.edit` |
| `/kit delete <id>` | Hapus kit | `kits.admin.delete` |
| `/kit cooldown <id> <detik>` | Ubah cooldown kit | `kits.admin.cooldown` |
| `/kit permission <id> [node\|none]` | Timpa permission kit secara manual (`none` = tanpa permission, semua orang boleh) | `kits.admin.permission` |
| `/kit description <id> <teks>` | Atur deskripsi kit (tampil di `/kit info` & GUI) | `kits.admin.description` |
| `/kit onetime <id> <true\|false>` | Jadikan kit sekali pakai per player (cooldown diabaikan kalau `true`) | `kits.admin.onetime` |
| `/kit addcommand <id> <player\|console> <command...>` | Tambah command yang dijalankan saat kit diklaim, sebagai player atau sebagai server/console | `kits.admin.command` |
| `/kit removecommand <id> <index>` | Hapus command dari kit (index sesuai nomor di `/kit info`) | `kits.admin.command` |

`/kit create`, `/kit edit` **harus** dijalankan oleh player (butuh akses
inventory) — ditolak kalau dijalankan dari console.

## Permission

| Permission | Default | Keterangan |
|---|---|---|
| `kits.use` | `true` | Izin dasar memakai `/kit` (list, info, claim). Semua player punya ini secara default. |
| `kits.admin.reload` | `op` | Reload config & data. |
| `kits.admin.create` | `op` | Buat kit baru. |
| `kits.admin.edit` | `op` | Edit isi item kit. |
| `kits.admin.delete` | `op` | Hapus kit. |
| `kits.admin.cooldown` | `op` | Ubah cooldown kit. |
| `kits.admin.permission` | `op` | Timpa permission kit secara manual. |
| `kits.admin.description` | `op` | Ubah deskripsi kit. |
| `kits.admin.onetime` | `op` | Ubah status sekali-pakai kit. |
| `kits.admin.command` | `op` | Tambah/hapus command isi kit. |
| `kits.vip` / `kits.mvp` / `kits.staff` | `false` | Contoh node per-tier (opsional) — didaftarkan supaya otomatis muncul di rank editor Prime BDS. |

**Permission per-kit itu dinamis**, bukan daftar di atas — setiap kit
punya node sendiri (default `kits.<id>`, atau custom lewat
`/kit permission`). Cek node persis suatu kit lewat `/kit info <id>`.

## Integrasi Permission (Prime BDS & server lain)

Plugin ini **tidak** memakai API khusus Prime BDS. Setelah membaca
langsung [source code Prime BDS](https://github.com/PrimeStrat/primebds),
ditemukan bahwa Prime BDS menerapkan permission langsung ke sistem
`Permissible` bawaan Endstone (`addAttachment` + `setPermission` +
`recalculatePermissions`) berdasarkan rank yang diatur admin. Karena
itu, plugin ini cukup memakai `has_permission()` standar — otomatis
kompatibel dengan Prime BDS maupun plugin permission lain yang
mengikuti pola serupa (gaya Bukkit/LuckPerms), tanpa kode integrasi
khusus.

Langkah pakainya:
1. `/kit create <id> <cooldown> [nama]` — otomatis membuat permission
   `kits.<id>`.
2. Di Prime BDS: `/rank perm add <rank> kits.<id>` — grant permission
   itu ke rank yang diinginkan.
3. Player dengan rank tersebut otomatis bisa klaim kit itu (efektif
   langsung tanpa perlu rejoin, berkat `recalculatePermissions`
   Prime BDS).

Catatan: karena permission kit dibuat saat *runtime* (bukan
dideklarasikan statis saat plugin dimuat), node ini tidak otomatis
muncul di daftar/autocomplete rank editor Prime BDS — API Python
Endstone saat ini belum menyediakan cara mendaftarkan permission baru
secara dinamis. Node tetap berfungsi penuh untuk pengecekan akses;
admin cukup tahu nama persisnya (`/kit info <id>`) saat mengetik
command grant di Prime BDS.

## Konfigurasi

`config.toml` (dibuat otomatis di folder data plugin):

```toml
prefix = "&8[&bKits&8] &r"

[messages]
no_permission     = "&cKamu tidak punya izin untuk kit ini."
cooldown_active   = "&eTunggu {time} lagi sebelum klaim ulang."
kit_claimed       = "&aKamu berhasil klaim kit {kit}."
kit_not_found     = "&cKit '{kit}' tidak ditemukan."
kit_created       = "&aKit '{kit}' berhasil dibuat."
claim_in_progress = "&eKlaim sebelumnya masih diproses, coba lagi sebentar."
inventory_full    = "&eInventory penuh, {count} stack item tidak muat dan hilang."

[cooldown]
time_format = "long"   # "long" -> "1 jam 20 menit", "short" -> "1j 20m"

[gui]
enabled = true
title = "Daftar Kit"
show_permission_in_lore = true   # belum dipakai, lihat catatan di bawah
show_time_remaining = true       # belum dipakai, lihat catatan di bawah

[storage]
kits_file = "kits.json"
database_file = "cooldowns.db"
sqlite_wal_mode = true

[permissions]
provider = "auto"   # belum dipakai, lihat catatan di bawah
```

Semua kode warna pakai `&` (bukan `§`) — otomatis di-translate ke
format asli Bedrock, jadi lebih aman diketik di file teks biasa.

**Catatan jujur soal 3 opsi yang belum berfungsi:** `gui.show_permission_in_lore`,
`gui.show_time_remaining`, dan `permissions.provider` ada di config
sebagai *reserved for future use* tapi **belum benar-benar dibaca** oleh
kode saat ini — GUI selalu menampilkan status cooldown, dan pengecekan
permission selalu memakai sistem native (yang sudah otomatis kompatibel
Prime BDS, lihat bagian sebelumnya). Mengubah 3 nilai ini di config
tidak akan berefek apa pun untuk saat ini.

## Struktur Proyek

```
src/endstone_kits/
├── plugin.py       # composition root (wiring), TIDAK ada business logic
├── config.toml     # default config, dicopy otomatis ke data folder
├── commands/       # parsing argumen & feedback pesan (kit_command.py = player, kit_admin_command.py = admin)
├── listeners/      # event handler Endstone (join/quit untuk cache cooldown)
├── managers/       # business logic murni:
│   ├── kit_manager.py               # CRUD kit, snapshot inventory
│   ├── cooldown_manager.py          # cek/catat cooldown, reserve-then-commit
│   ├── permission_manager.py        # cek akses kit berdasarkan permission
│   ├── command_execution_manager.py # jalankan command isi kit
│   └── gui_manager.py               # kapan form dibuka, data apa isinya
├── models/         # dataclass domain: Kit, KitItemData, KitCommandEntry, PlayerCooldown
├── storage/        # akses fisik ke file/DB (Repository Pattern): JSON untuk kit, SQLite untuk cooldown
├── services/       # adapter ke Endstone API spesifik:
│   ├── item_serializer.py     # ItemStack <-> KitItemData
│   ├── placeholder_service.py # {player}, {uuid}
│   └── permission_provider.py # abstraksi has_permission (native, kompatibel Prime BDS)
├── gui/            # bentuk visual form (ActionForm) -- murni tampilan, tanpa logic
├── utils/          # helper stateless: format_duration, translate_color_codes
└── config/         # wrapper tipis (KitsConfig) di atas self.config bawaan Endstone
```

Penjelasan arsitektur lengkap (alasan tiap keputusan desain, roadmap
tahap pengembangan) ada di [`docs/kits-plugin-design.md`](docs/kits-plugin-design.md).

## Penyimpanan Data

- **Kit (`kits.json`)** — JSON, karena jumlahnya kecil & jarang berubah
  (hanya saat admin create/edit/delete), dan strukturnya nested (kit →
  list item → enchant/lore/dll). Ditulis dengan atomic write (temp file
  + rename) supaya tidak korup kalau server crash di tengah penulisan.
- **Cooldown (`cooldowns.db`)** — SQLite (WAL mode), karena data ini
  sering ditulis (tiap klaim kit) dan tumbuh besar (player × kit).
  Composite primary key `(player_uuid, kit_id)` untuk update baris
  tunggal & query cepat per player.

## Batasan yang Diketahui

- **Custom Model Data**: field tersedia di model data tapi selalu
  kosong hasil serialize — Bedrock tidak punya konsep ini seperti Java
  Edition/Paper.
- **NBT mentah**: disimpan sebagai string SNBT hanya untuk
  referensi/debug admin, **tidak** dipakai untuk merekonstruksi item
  saat kit diklaim (belum ada cara aman terverifikasi untuk parse SNBT
  kembali tanpa risiko merusak item). Metadata fungsional (nama, lore,
  damage, enchant, unbreakable) sudah tercakup penuh lewat jalur lain.
- **Command gagal saat klaim** tidak membatalkan item yang sudah
  diberikan (rollback item tidak sepele di Bedrock); command lain
  dalam kit yang sama tetap lanjut dijalankan walau satu gagal.
- **Permission dinamis** (dibuat runtime lewat `/kit create`/
  `/kit permission`) tidak otomatis terdaftar ke UI rank editor Prime
  BDS (lihat [Integrasi Permission](#integrasi-permission-prime-bds--server-lain)).
- Tiga opsi config (`gui.show_permission_in_lore`,
  `gui.show_time_remaining`, `permissions.provider`) belum
  diimplementasikan (lihat [Konfigurasi](#konfigurasi)).

## Development

Semua business logic (`managers/`, `models/`, sebagian besar
`services/`) sengaja ditulis agar bisa diuji **tanpa** server Endstone
menyala, lewat mock/stub repository & objek palsu. Lihat riwayat
pengembangan di `docs/kits-plugin-design.md` untuk contoh pola testing
tiap komponen.

```bash
pip install -e .          # editable install untuk development
python -m py_compile $(find src -name "*.py")   # cek sintaks cepat
```
