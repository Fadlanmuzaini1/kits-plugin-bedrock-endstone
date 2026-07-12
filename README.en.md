# Endstone Kits

A **Kits** plugin for Minecraft Bedrock servers running on
[Endstone](https://endstone.dev). Admins build kits directly from
their own inventory (fully preserving enchantments, lore, custom
names, and durability), players claim them via command or GUI, with
per-player-per-kit cooldowns that persist across restarts and per-kit
permissions that integrate automatically with the server's permission
system (including [Prime BDS](https://github.com/PrimeStrat/primebds)).

## Key Features

- **Create kits from inventory** — a kit's contents (items + full
  metadata) are captured directly from the admin's inventory when
  creating a kit via command; no manual item configuration needed.
- **Full item metadata** — custom name, lore, enchantments, durability
  (damage), and unbreakable status are all preserved and restored
  intact when a kit is claimed.
- **Per-player, per-kit cooldown** — configured per kit, tracked
  separately for each player, and **persists across server restarts**
  (stored in SQLite, not just in memory).
- **One-time kits** — an option to make a kit claimable only ONCE per
  player, forever (great for starter/registration kits), independent
  of the regular cooldown setting.
- **Automatic permission** — every new kit automatically gets a
  `kits.<kit_name>` permission, which can be overridden manually at any
  time. Integrates with Prime BDS with zero extra configuration (see
  [Permission Integration](#permission-integration-prime-bds--other-servers)).
- **Kit commands** — a kit can run additional commands when claimed
  (e.g. effects, messages, teleports), executed **either as the
  claiming player or as the server/console** (chosen per command via
  `/kit addcommand`), with `{player}` and `{uuid}` placeholders.
- **GUI and text commands** — `/kit` with no arguments opens a kit
  selection form on the Bedrock client (can be disabled via config),
  or the plugin can still be used purely through text commands.
- **Multiple kits** — a single player can have access to many kits at
  once; each kit's cooldown is tracked independently.

## Installation

1. Build the plugin wheel (requires Python 3.10+ and the `endstone`
   package installed in the same environment as the server):
   ```bash
   pip install -e .
   ```
   or build a regular wheel (`pip install build && python -m build`)
   and install it however your server loads Python Endstone plugins.
2. Start/restart the server. The plugin automatically creates:
   - `config.toml` — configuration file (see [Configuration](#configuration)).
   - `kits.json` — data for every kit created by admins.
   - `cooldowns.db` — per-player, per-kit cooldown data (SQLite).

   All three are created in the plugin's data folder (typically
   `plugins/Kits/` or similar, depending on your server setup).

## Commands

| Command | Description | Permission |
|---|---|---|
| `/kit` | Opens the kit selection GUI (if `gui.enabled: true` and the sender is a player), or shows a text list otherwise | `kits.use` |
| `/kit list` | Shows the list of kits the sender can access (already permission-filtered) | `kits.use` |
| `/kit info <id>` | Shows kit details: name, description, permission, cooldown, item & command count | `kits.use` |
| `/kit claim <id>` | Claims a kit (checks permission & cooldown, grants items, runs the kit's commands) | `kits.use` |
| `/kit reload` | Reloads `config.toml` and `kits.json` from disk | `kits.admin.reload` |
| `/kit create <id> <cooldown_seconds> [display name]` | Creates a new kit from the sender's inventory. Automatically gets permission `kits.<id>` | `kits.admin.create` |
| `/kit edit <id>` | Replaces the kit's items with the sender's current inventory (metadata is untouched) | `kits.admin.edit` |
| `/kit delete <id>` | Deletes a kit | `kits.admin.delete` |
| `/kit cooldown <id> <seconds>` | Changes a kit's cooldown | `kits.admin.cooldown` |
| `/kit permission <id> [node\|none]` | Manually overrides a kit's permission (`none` = no permission required, open to everyone) | `kits.admin.permission` |
| `/kit description <id> <text>` | Sets a kit's description (shown in `/kit info` and the GUI) | `kits.admin.description` |
| `/kit onetime <id> <true\|false>` | Makes a kit claimable only once per player (cooldown is ignored when `true`) | `kits.admin.onetime` |
| `/kit addcommand <id> <player\|console> <command...>` | Adds a command to run when the kit is claimed, either as the player or as the server/console | `kits.admin.command` |
| `/kit removecommand <id> <index>` | Removes a command from a kit (index matches the number shown in `/kit info`) | `kits.admin.command` |

`/kit create` and `/kit edit` **must** be run by a player (they need
inventory access) — they're rejected when run from console.

## Permissions

| Permission | Default | Notes |
|---|---|---|
| `kits.use` | `true` | Base permission to use `/kit` (list, info, claim). Every player has this by default. |
| `kits.admin.reload` | `op` | Reload config & data. |
| `kits.admin.create` | `op` | Create a new kit. |
| `kits.admin.edit` | `op` | Edit a kit's items. |
| `kits.admin.delete` | `op` | Delete a kit. |
| `kits.admin.cooldown` | `op` | Change a kit's cooldown. |
| `kits.admin.permission` | `op` | Manually override a kit's permission. |
| `kits.admin.description` | `op` | Change a kit's description. |
| `kits.admin.onetime` | `op` | Change a kit's one-time status. |
| `kits.admin.command` | `op` | Add/remove a kit's commands. |
| `kits.vip` / `kits.mvp` / `kits.staff` | `false` | Example per-tier nodes (optional) — pre-declared so they automatically show up in Prime BDS's rank editor. |

**Per-kit permissions are dynamic**, not the fixed list above — every
kit gets its own node (default `kits.<id>`, or a custom one via
`/kit permission`). Check a kit's exact node with `/kit info <id>`.

## Permission Integration (Prime BDS & other servers)

This plugin does **not** use any Prime BDS-specific API. After reading
[Prime BDS's source code](https://github.com/PrimeStrat/primebds)
directly, it turns out Prime BDS applies permissions straight onto
Endstone's built-in `Permissible` system (`addAttachment` +
`setPermission` + `recalculatePermissions`) based on the ranks admins
configure. Because of that, this plugin only needs the standard
`has_permission()` call — it's automatically compatible with Prime BDS
and any other permission plugin that follows a similar (Bukkit/
LuckPerms-style) pattern, with no special integration code required.

Usage:
1. `/kit create <id> <cooldown> [name]` — automatically creates
   permission `kits.<id>`.
2. In Prime BDS: `/rank perm add <rank> kits.<id>` — grant that
   permission to the desired rank.
3. Players with that rank can immediately claim the kit (takes effect
   right away thanks to Prime BDS's `recalculatePermissions`, no
   rejoin needed).

Note: because kit permissions are created at *runtime* (not statically
declared when the plugin loads), the node won't automatically appear
in Prime BDS's rank editor list/autocomplete — the current Endstone
Python API doesn't provide a way to dynamically register new
permissions. The node still works perfectly for access checks; admins
just need to know its exact name (`/kit info <id>`) when typing the
grant command in Prime BDS.

## Configuration

`config.toml` (created automatically in the plugin's data folder):

```toml
prefix = "&8[&bKits&8] &r"

[messages]
no_permission     = "&cYou don't have permission for this kit."
cooldown_active   = "&eWait {time} before claiming again."
kit_claimed       = "&aYou successfully claimed kit {kit}."
kit_not_found     = "&cKit '{kit}' not found."
kit_created       = "&aKit '{kit}' created successfully."
claim_in_progress = "&eThe previous claim is still being processed, try again shortly."
inventory_full    = "&eInventory full, {count} stack(s) didn't fit and were lost."

[cooldown]
time_format = "long"   # "long" -> "1 hour 20 minutes", "short" -> "1h 20m"

[gui]
enabled = true
title = "Kit List"
show_permission_in_lore = true   # not yet used, see note below
show_time_remaining = true       # not yet used, see note below

[storage]
kits_file = "kits.json"
database_file = "cooldowns.db"
sqlite_wal_mode = true

[permissions]
provider = "auto"   # not yet used, see note below
```

All color codes use `&` (not `§`) — automatically translated to
Bedrock's native format, which is safer to type in a plain text file.

**Honest note on 3 options that don't do anything yet:**
`gui.show_permission_in_lore`, `gui.show_time_remaining`, and
`permissions.provider` exist in the config as *reserved for future
use* but are **not actually read** by the current code — the GUI
always shows cooldown status, and permission checks always use the
native system (which is already automatically Prime BDS-compatible,
see the section above). Changing these three values currently has no
effect.

## Project Structure

```
src/endstone_kits/
├── plugin.py       # composition root (wiring only), NO business logic
├── config.toml     # default config, auto-copied to the data folder
├── commands/       # argument parsing & message feedback (kit_command.py = player, kit_admin_command.py = admin)
├── listeners/      # Endstone event handlers (join/quit, for cooldown cache)
├── managers/       # pure business logic:
│   ├── kit_manager.py               # kit CRUD, inventory snapshotting
│   ├── cooldown_manager.py          # cooldown check/record, reserve-then-commit
│   ├── permission_manager.py        # kit access checks based on permission
│   ├── command_execution_manager.py # runs a kit's commands
│   └── gui_manager.py               # when a form opens, what data it shows
├── models/         # domain dataclasses: Kit, KitItemData, KitCommandEntry, PlayerCooldown
├── storage/        # physical file/DB access (Repository Pattern): JSON for kits, SQLite for cooldowns
├── services/       # adapters to Endstone-specific APIs:
│   ├── item_serializer.py     # ItemStack <-> KitItemData
│   ├── placeholder_service.py # {player}, {uuid}
│   └── permission_provider.py # has_permission abstraction (native, Prime BDS-compatible)
├── gui/            # form visuals (ActionForm) -- pure presentation, no logic
├── utils/          # stateless helpers: format_duration, translate_color_codes
└── config/         # thin wrapper (KitsConfig) around Endstone's built-in self.config
```

The full architecture write-up (reasoning behind every design decision,
the development roadmap) lives in
[`docs/kits-plugin-design.md`](docs/kits-plugin-design.md).

## Data Storage

- **Kits (`kits.json`)** — JSON, because there are usually few kits
  and they change rarely (only on admin create/edit/delete), and the
  structure is nested (kit → item list → enchants/lore/etc.). Written
  with an atomic write (temp file + rename) so it can't get corrupted
  if the server crashes mid-write.
- **Cooldowns (`cooldowns.db`)** — SQLite (WAL mode), because this
  data is written often (every kit claim) and grows large (players ×
  kits). Composite primary key `(player_uuid, kit_id)` for single-row
  updates and fast per-player queries.

## Known Limitations

- **Custom Model Data**: the field exists in the data model but is
  always empty from serialization — Bedrock has no equivalent concept
  to Java Edition/Paper's Custom Model Data.
- **Raw NBT**: stored as an SNBT string purely for admin
  reference/debugging, **not** used to reconstruct the item when a kit
  is claimed (there's no verified-safe way yet to parse SNBT back
  without risking item corruption). Functional metadata (name, lore,
  damage, enchants, unbreakable) is already fully covered through
  other means.
- **A failed command during claim** does not roll back items already
  granted (item rollback isn't trivial on Bedrock); other commands in
  the same kit still run even if one fails.
- **Dynamically created permissions** (via `/kit create` /
  `/kit permission`) don't automatically register in Prime BDS's rank
  editor UI (see [Permission Integration](#permission-integration-prime-bds--other-servers)).
- Three config options (`gui.show_permission_in_lore`,
  `gui.show_time_remaining`, `permissions.provider`) are not yet
  implemented (see [Configuration](#configuration)).

## Development

Nearly all business logic (`managers/`, `models/`, most of
`services/`) is deliberately written to be testable **without** an
Endstone server running, using mock/stub repositories and fake
objects. See the development history in `docs/kits-plugin-design.md`
for examples of the testing pattern used for each component.

```bash
pip install -e .          # editable install for development
python -m py_compile $(find src -name "*.py")   # quick syntax check
```
