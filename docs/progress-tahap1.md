# Endstone Kits

Plugin sistem Kits untuk server Endstone (Minecraft Bedrock).

Status: **Tahap 1 — Fondasi** (lihat `docs/kits-plugin-design.md` untuk
roadmap lengkap).

## Yang sudah ada di Tahap 1

- Struktur proyek & entry point plugin (`plugin.py`) yang bisa di-load Endstone.
- Konfigurasi (`config.toml`) via mekanisme `self.config` bawaan Endstone,
  dibungkus `KitsConfig` (`config/config_schema.py`) supaya akses config
  bertipe & aman dari `KeyError` saat versi lama.
- Lapisan storage:
  - `storage/base.py` — interface `KitRepository` & `CooldownRepository`.
  - `storage/json_kit_repository.py` — implementasi kit definitions
    berbasis JSON dengan atomic write.
  - `storage/sqlite_cooldown_repository.py` — implementasi cooldown
    per-player-per-kit berbasis SQLite (WAL mode).
- Command `/kit` (info dasar) dan `/kit reload` (reload config) sebagai
  bukti seluruh wiring (config -> storage -> command) berjalan.

Business logic (KitManager, CooldownManager, dll.) BELUM ada di tahap
ini secara sengaja — akan ditambahkan mulai Tahap 2 sesuai roadmap.

## Menjalankan untuk development

```bash
# di root proyek, dengan venv yang sudah berisi package `endstone`
pip install -e .
```

Lalu arahkan Endstone server untuk memuat package ini dari environment
yang sama (lihat panduan "Install your plugin" di dokumentasi Endstone
untuk mode pengembangan / editable install).

## Struktur folder

```
src/endstone_kits/
├── plugin.py       # composition root, TIDAK ada business logic
├── config.toml     # default config, dicopy otomatis ke data folder
├── commands/       # parsing argumen & feedback pesan
├── listeners/      # event handler Endstone
├── managers/       # business logic murni
├── models/         # dataclass domain (Kit, KitItemData, dll.)
├── storage/        # akses fisik ke file/DB (Repository Pattern)
├── services/       # adapter ke Endstone API / sistem eksternal
├── gui/            # bentuk visual form (ActionForm/ModalForm)
├── events/         # custom event untuk extensibility
├── utils/          # helper stateless
└── config/         # wrapper tipis di atas self.config
```
