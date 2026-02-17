## TODO — Next Sessions

**Cleaning Session (dedicated)**
- Apply `cleaner.py` functions throughout builder.py M3U output
- `clean_m3u_title()` on all playlist entries
- `clean_display_title()` in favorites menu labels
- `clean_folder_name()` on auto-created delivery subfolders
- Strip metadata post-download (wire `strip_file_metadata()` into `_post_download()`)

**Intelligence — finish wiring**
- `extract_yt_meta()` called in engine.py after yt-dlp download, saved via `db.add_favorite(yt_meta=...)`
- `classify_content()` result used to suggest bucket in context menu `_add_to_favorite()`
- `suggest_discrete_folder()` used in delivery when content classified private
- `build_folder_structure()` tested with real paths

**Features still open**
- Duplicate detection (Pro setting exists, no implementation)
- DB encryption (Pro setting exists, no implementation)
- Smart learning (Pro setting exists, no implementation)
- Resume/retry — `pro_resume_downloads` setting exists, not wired in engine
- `auto_favorite` setting in Advanced mode referenced in engine but not in settings.xml
- Connection profiles (Pro setting exists, no implementation)
- Playlist color phase (explicitly deferred)
- Meta module background queue not fully wired

**From your comments**
- Name decision: Fluid / FluidSnoop / FluidMedia / FluidHub — then global rename
- Icon + fanart placement, verify paths in addon.xml
- Local `__init__.py` files to create for each module folder



Plus:


Corrected flow:

1. If playing → *"Video is playing. Stop watching to download?"*
   - **Yes** → stop playback
   - **No** → keep playing (download runs in background)
2. Either way → *"Start download?"* OK / Cancel
3. OK → queue → toast *"Queued"*
4. Cancel → nothing

---

**TODO added — full spec:**

- Implement corrected playing-check flow in `context.py`
- Queue complete popup: *"X files downloaded"* (single, end of queue only)
- Add `kodi.notify_if_idle(msg)` to `kodi_utils.py` — suppresses non-critical notifications during playback
- Apply `notify_if_idle` to: playlist batch update, meta fetch, delivery queue processor
- Audit all `kodi.notify()` calls — classify each as critical (always show) or idle-only (suppress during playback)

A few genuine additions:

**Technical loose ends**
- `context_favorite.py` needs to be created — referenced in addon.xml but doesn't exist yet
- `plugin.program.fluid` vs `plugin.video.fluid` — the addon ID in `addon.xml` must match the folder name exactly, and all internal references (`logger.py` addon_id, `strings.po` header, GitHub URL) need to align once name is decided
- `script.module.requests` import in addon.xml — verify if actually used, remove if not

**Robustness**
- No handling if yt-dlp is outdated (returns error on newer sites) — worth a version check or graceful error message pointing user to update
- WebDAV delivery has no connection timeout — a hanging delivery blocks the service queue indefinitely
- `get_favorites()` with `order_by` param accepts raw string — SQL injection risk if ever exposed to user input, needs whitelist validation

**UX gaps**
- No way to edit or delete a favorite from within Kodi — only add and export
- No visual indicator in main menu that downloads are actively running
- First-run wizard sets download path but doesn't verify it's writable

**For the cleaning session**
- Decide: does `clean_display_title()` also handle CamelCase splitting? (`FluidIntro` → `Fluid Intro`) — common in YouTube filenames
- Thumbnail handling for non-YouTube sources is undefined — fallback needed

**Longer term**
- `meta/fetcher.py` background queue not wired — currently fetch is always interactive
- No way to merge or rename buckets
- Playlist profiles stored in addon settings (4KB cap) — migration to JSON file before it silently truncates

. WebDAV = read/stream only in your setup. Noted.

**TODO — Remote delivery options:**

- Remove WebDAV as a delivery protocol (keep as source for playlist scanning only)
- Add delivery via:
  - **SMB** — already works via `xbmcvfs.copy()` to `smb://` paths
  - **SSH/SFTP** — via `paramiko` (Python lib, needs bundling or Termux handoff)
  - **rclone** — shell call to system rclone, most flexible (covers all cloud providers), same Termux handoff pattern already in place
  - **Termux handoff** — already exists for downloads, extend to delivery commands

**Practical suggestion:** rclone is the highest value addition. One integration covers Google Drive, Dropbox, OneDrive, S3, SFTP and more. Pattern mirrors Termux download fallback exactly — build the command, hand off, done. No library bundling needed.

**Blueprint update:**
- WebDAV paths in delivery rules → flag as "source only, not delivery target"
- Warn user in settings if they set a `davs://` delivery destination

**TODO: delivery capability matrix**

User sees only what's available for their setup:

| Method | Requires | Without Termux | With Termux |
|---|---|---|---|
| Local/SMB | nothing | ✅ | ✅ |
| rclone | rclone installed | ❌ | ✅ via handoff |
| SFTP/SSH | paramiko or rclone | ❌ | ✅ via handoff |
| WebDAV | — | source only | source only |

**Implementation:**
- On first run / settings open: detect Termux, detect rclone, detect paramiko
- Show only available delivery methods — no dead options
- If method selected but dependency missing: clear message + what to install
- `help.txt` gets a dependencies section per delivery method

**Add to TODO:**
- Capability detection function in `intelligence.py` or new `core/capabilities.py`
- Settings delivery method list filtered by detected capabilities
- Help text per method: what it needs, how to install (Termux pkg, pip, etc.)
- Extend first-run wizard: if Termux detected, offer to configure rclone remote
... 
I don't know where termux can help or python can do it similar, then I would suggest: use global method first, only add termux & hide behind   pro or dev... If the difference is minimal keep global for all users. 
... 

Correct logic.

**Rule: Python-native first, always.**

- If Python (via `xbmcvfs`, `shutil`, `paramiko`, `subprocess`) can do it cleanly → use it, available to all users
- If it needs system binaries (rclone) → subprocess call, works without Termux on desktop/rooted Android
- Termux only adds value when: binary not available in Kodi's sandboxed environment (mainly Android non-rooted)
- Hide Termux-specific options behind Pro/Dev

**Practical result:**
- SMB → `xbmcvfs`, all users
- SFTP/SSH → `paramiko` pip install, all users who have it
- rclone → subprocess, works if rclone installed at system level
- Termux handoff → Pro only, fallback when above fails on sandboxed Android

**TODO update:** capability detection checks Python libs first, system binaries second, Termux last. User sees one clean list, complexity hidden.