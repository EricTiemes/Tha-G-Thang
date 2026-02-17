# FLUID Addon — Session Handoff
_Last updated: 15 Feb 2026_

---

## BEFORE NEXT SESSION

### Decide first (blocks other work)
- [ ] **Addon name** — Fluid / FluidSnoop / FluidMedia / FluidHub
  - Once decided: update `addon.xml` (id, name, source URL), `logger.py` (addon_id), `strings.po` header, folder name
- [ ] **Place** `resources/icon.png` and `resources/fanart.jpg`
- [ ] **Create** empty `__init__.py` in each module folder locally:
  `modules/downloader/`, `modules/delivery/`, `modules/favorites/`, `modules/playlist/`, `modules/meta/`

### Fix before first test
- [ ] `addon.xml` line 21 — correct visible tag (currently malformed):
  ```xml
  <visible>String.IsEqual(ListItem.DBTYPE,video) | ListItem.IsPlayable</visible>
  ```
- [ ] `addon.xml` — add second extension for Programs category:
  ```xml
  <extension point="xbmc.python.script" library="default.py">
      <provides>executable</provides>
  </extension>
  ```
- [ ] `addon.xml` — verify `script.module.requests` is actually used; remove if not
- [ ] `addon.xml` id must match folder name exactly
- [ ] Add `auto_favorite` setting to `settings.xml` Advanced section (referenced in `engine.py`, missing from xml)

---

## TODO — PRIORITY ORDER

### 1. Create missing files
- [ ] `context_favorite.py` — referenced in `addon.xml`, does not exist
  - Skips menu, calls `_add_to_favorite()` directly from `context.py`
- [ ] Empty `__init__.py` per module folder (do locally)

### 2. Context menu — download flow (spec)
File: `context.py`

When Download selected and video is playing:
1. Dialog: *"Video is playing. Stop watching to download?"*
   - Yes → stop playback
   - No → keep playing
2. Either way → Dialog: *"Start download?"* OK / Cancel
3. OK → queue → toast: *"Queued"*
4. Cancel → nothing

Queue messaging:
- No per-file popups during queue processing
- Single popup when full queue empties: *"X files downloaded"*

### 3. Playback-aware notifications
File: `core/kodi_utils.py`

- Add `notify_if_idle(msg)` — checks `xbmc.Player().isPlaying()` before notifying
- Apply to: playlist batch update, meta fetch, delivery queue processing
- Audit all `kodi.notify()` calls — mark each critical (always show) or idle-only
- Background service processes must not interrupt playback with popups

### 4. Intelligence — finish wiring
- [ ] `engine.py` — call `extract_yt_meta()` after yt-dlp download; save via `db.add_favorite(yt_meta=...)`
- [ ] `context.py` `_add_to_favorite()` — use `classify_content()` to pre-select bucket suggestion
- [ ] Delivery — use `suggest_discrete_folder()` when classified content is private
- [ ] Test `build_folder_structure()` with real local and SMB paths

### 5. Cleaning session (dedicated)
- [ ] `builder.py` — apply `clean_m3u_title()` to all M3U entries
- [ ] `FavoritesManager.py` — apply `clean_display_title()` to menu labels
- [ ] Delivery — apply `clean_folder_name()` to auto-created subfolders
- [ ] `engine.py` `_post_download()` — call `strip_file_metadata()` when privacy enabled
- [ ] Decide: does `clean_display_title()` split CamelCase? (`FluidIntro` → `Fluid Intro`) — common in YouTube filenames
- [ ] Thumbnail fallback for non-YouTube sources

### 6. Remote delivery
Current state: WebDAV = source/stream only (not delivery). SMB works via `xbmcvfs`.

Rule — **Python-native first:**
| Method | How | Availability |
|---|---|---|
| Local | `shutil` | All users |
| SMB | `xbmcvfs.copy()` | All users |
| SFTP/SSH | `paramiko` | All users (if installed) |
| rclone | `subprocess` | All users (if installed at system level) |
| Termux handoff | shell | Pro/Dev only — Android non-rooted fallback |

- [ ] `core/capabilities.py` — detect available methods at runtime (Python libs → system binaries → Termux)
- [ ] Settings delivery method list filtered by detected capabilities
- [ ] Warn user if `davs://` path set as delivery destination
- [ ] `help.txt` — add dependencies section per delivery method
- [ ] Extend first-run wizard: if rclone detected, offer to configure remote

### 7. Robustness fixes
- [ ] yt-dlp version check — graceful error if outdated, prompt user to update
- [ ] Delivery queue — add connection timeout for SMB/remote (currently hangs indefinitely)
- [ ] `get_favorites(order_by=)` — whitelist allowed values, SQL injection risk if exposed to user input
- [ ] First-run wizard — verify download path is writable before accepting

### 8. UX gaps
- [ ] Favorites — add edit and delete item actions within Kodi
- [ ] Main menu — visual indicator when downloads are actively running
- [ ] Playlist profiles — migrate storage from `addon.setSetting()` (4KB cap) to JSON file in `profile_path`

---

## DEFERRED / LATER

Settings exist, no implementation yet — build when core is stable:
- Duplicate detection (Pro)
- DB encryption (Pro)
- Smart learning (Pro)
- Resume/retry downloads (`pro_resume_downloads`)
- Connection profiles (Pro)
- Merge / rename buckets
- `meta/fetcher.py` background queue (currently interactive only)
- Playlist color phase (explicitly next phase)

---

## BLUEPRINT — RULES WE FOLLOW

### Architecture
- Modular — each feature is a self-contained folder under `modules/`
- Auto-discovery via `modules/__init__.py` — adding a module = zero changes to core
- Each module exposes `MODULE_ROUTES` dict — router never hardcodes module internals
- `core/` = shared tools only, no business logic

### Central tools (core/)
| File | Owns |
|---|---|
| `intelligence.py` | Pattern matching, classification, URL building, yt-meta extraction |
| `cleaner.py` | All text and file cleaning |
| `database.py` | Single DB connection point, query/execute/one helpers |
| `config.py` | All settings access — never raw `addon.getSetting()` outside this file |
| `kodi_utils.py` | All Kodi UI calls, theme, dialogs, playback checks |
| `logger.py` | All logging |

### URL safety — absolute rule
`is_url()` checked before any string manipulation.
Never modify: `http://` `https://` `plugin://` `davs://` `smb://` `special://` `rtmp://` `rtsp://` `nfs://`
Applies in cleaner, builder, intelligence — everywhere without exception.

### Intelligence
- No preset categories — learns from user's own bucket names, folder names, delivery rule keywords
- Private bucket names never indexed as classification keywords
- `classify_content()` → suggests bucket + folder from user vocabulary
- `extract_yt_meta()` → saves channel, upload_date, duration, view_count, tags, categories, description (300 chars), playlist

### Settings
- Three tiers: Simple / Advanced / Pro — visibility by `eq(settings_mode,value)`
- Module enable + menu visibility are separate toggles
- Core modules (downloader, delivery) default `True`; optional modules default `False`
- Discrete naming templates: independent for folders and buckets (`_` / `__` / custom)

### Menus & context
- Context shows only settings-enabled items, capped at `context_max_items`
- Single item → executes directly, no submenu
- `Add to Favorites` always asks which bucket
- Main menu shows only enabled + visible modules
- Two context entries: Download (conditional) + Save to Favorites (always visible)

### Flow
- Background: queued → service picks up (30s) → yt-dlp → delivery queued → delivered
- One download at a time — no device strain during playback
- Copy vs move: `move_files` setting
- Remote delivery: `delete_after_remote` setting
- Private content: discrete template applied to path, content type never in folder name

### Delivery
- WebDAV: source/playlist scanning only — never a delivery target
- Python-native first → system binaries → Termux (Pro/Dev only)
- Capability detection at runtime — user sees only available options

### Privacy
- Private buckets: never in paths, never indexed as keywords
- Timestamp filenames optional
- EXIF/metadata strip optional
- Obfuscated bucket display names optional
- Minimal metadata storage optional

### Notifications
- Critical (always show): errors, user-initiated actions
- Idle-only (suppress during playback): queue progress, batch updates, background completions
- Queue complete: single popup only, not per-file

---

## CURRENT FILE STRUCTURE

```
plugin.video.fluid/
├── addon.xml
├── default.py
├── service.py
├── context.py
├── context_favorite.py          ← TO CREATE
│
└── resources/
    ├── icon.png                 ← you place
    ├── fanart.jpg               ← you place
    ├── help.txt
    ├── language/
    │   └── English/
    │       └── strings.po
    ├── settings.xml
    └── lib/
        ├── core/
        │   ├── config.py
        │   ├── database.py
        │   ├── intelligence.py
        │   ├── cleaner.py
        │   ├── kodi_utils.py
        │   ├── router.py
        │   └── logger.py
        └── modules/
            ├── __init__.py
            ├── downloader/
            │   ├── __init__.py  ← create locally
            │   └── engine.py
            ├── delivery/
            │   ├── __init__.py  ← create locally
            │   └── DeliveryRouter.py
            ├── favorites/
            │   ├── __init__.py  ← create locally
            │   └── FavoritesManager.py
            ├── playlist/
            │   ├── __init__.py  ← create locally
            │   └── builder.py
            └── meta/
                ├── __init__.py  ← create locally
                └── fetcher.py
```

---

## FILES DELIVERED THIS SESSION
_All are complete replacements — always use latest output version._

| File | Notes |
|---|---|
| `default.py` | Module auto-discovery + first-run wizard |
| `service.py` | Download worker added — background mode now works end-to-end |
| `context.py` | Bucket picker, playback-aware, correct imports |
| `context_favorite.py` | Referenced in addon.xml — still to create |
| `router.py` | Inline queue view, fixed imports, setup_wizard route |
| `engine.py` | Uses intelligence, folder structure, MODULE_ROUTES |
| `DeliveryRouter.py` | Uses intelligence, WebDAV note, MODULE_ROUTES |
| `FavoritesManager.py` | Uses intelligence, export_to_json, MODULE_ROUTES |
| `builder.py` | Fully rewritten — profiles, WebDAV, priority sort, STRM export |
| `modules/__init__.py` | Keep populated — do NOT empty |
| `core/intelligence.py` | User-vocabulary driven, yt-meta, discrete templates |
| `core/cleaner.py` | Display/filename/URL-safe, EXIF strip, DB purge |
| `core/database.py` | query/execute/one helpers, yt_meta in add_favorite |
| `core/config.py` | Module defaults fixed, discrete template properties |
| `core/logger.py` | Correct Kodi log levels |
| `addon.xml` | Duplicate extension removed — still needs visible fix (see above) |
| `settings.xml` | All tiers, move/delete/folder-structure settings, discrete naming |
| `strings.po` | All new string IDs |
| `resources/help.txt` | User guide — aim, features, flows, intelligence |
... 
Agreed — clean approach:

- Filename = cleaned title, always readable
- Discrete = folder path only (`_` / `__`)
- No title masking, no timestamp filenames
- Timestamp lives in DB/meta only, used for sorting

Update `build_filename()` — remove privacy_mode timestamp logic entirely. Update `help.txt` wording to match your "Personal downloaded, discrete, content" phrasing.

Adding to handoff. See you in a bit.
