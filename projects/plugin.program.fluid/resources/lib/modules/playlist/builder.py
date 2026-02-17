import os
import re
import json
import sqlite3
import urllib.parse
from datetime import datetime

import xbmc
import xbmcgui
import xbmcvfs

from core.config import config
from core.database import db
from core.kodi_utils import kodi
from core.logger import logger


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLAYLIST_SAVE_DIR = "special://profile/playlists/videos/"
PROFILES_KEY = "playlist_profiles"          # stored via config.set_setting
SUPPORTED_EXTS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv',
    '.m4v', '.flv', '.webm', '.ts', '.mpg', '.mpeg'
}
SCAN_DEPTH = 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_title(raw: str) -> str:
    """Strip extension, decode %XX, replace underscores/dashes with spaces, collapse whitespace."""
    # Remove extension
    base = os.path.splitext(raw)[0]
    # URL-decode
    base = urllib.parse.unquote(base)
    # Replace underscores/dashes that act as spaces
    base = base.replace('_', ' ').replace('-', ' ')
    # Collapse multiple spaces
    base = re.sub(r' +', ' ', base).strip()
    return base


def _file_mtime(path: str) -> float:
    """Return modification time of a file via xbmcvfs; fallback to 0."""
    try:
        stat = xbmcvfs.Stat(path)
        return stat.st_mtime()
    except Exception:
        return 0.0


def _is_priority(text: str, keywords: list) -> bool:
    """True if any priority keyword appears in text (case-insensitive)."""
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords if kw.strip())


def _scan_folder(base_path: str, depth: int = SCAN_DEPTH) -> list:
    """
    Recursively scan a folder for media files up to `depth` levels.
    Returns list of dicts: {path, title, parent, mtime}
    Supports local paths and davs:// / smb:// via xbmcvfs.
    """
    entries = []
    if depth < 0:
        return entries

    try:
        dirs, files = xbmcvfs.listdir(base_path)
    except Exception as e:
        logger.warning(f"Cannot list {base_path}: {e}")
        return entries

    # Normalise base_path trailing separator
    if not base_path.endswith('/'):
        base_path += '/'

    parent_name = base_path.rstrip('/').split('/')[-1]

    for fname in files:
        ext = os.path.splitext(fname)[1].lower()
        if ext not in SUPPORTED_EXTS:
            continue
        full_path = base_path + fname
        entries.append({
            'path':   full_path,
            'title':  _clean_title(fname),
            'parent': parent_name,
            'mtime':  _file_mtime(full_path),
            'source': 'folder',
        })

    for d in dirs:
        sub = base_path + d + '/'
        entries.extend(_scan_folder(sub, depth - 1))

    return entries


def _fetch_bucket_entries(bucket_id: int) -> list:
    """Return favorites from a bucket as playlist entries."""
    entries = []
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.url, f.title, c.name, f.created_at
            FROM favorites f
            JOIN categories c ON f.category_id = c.id
            WHERE f.category_id = ?
            ORDER BY f.created_at DESC
        """, (bucket_id,))
        rows = cursor.fetchall()
        conn.close()

        for url, title, cat_name, created_at in rows:
            # Parse created_at to a comparable float
            try:
                mtime = datetime.fromisoformat(created_at).timestamp()
            except Exception:
                mtime = 0.0

            entries.append({
                'path':   url,
                'title':  _clean_title(title or url),
                'parent': cat_name or 'Favorites',
                'mtime':  mtime,
                'source': 'bucket',
            })
    except Exception as e:
        logger.error(f"Fetch bucket {bucket_id} failed: {e}")
    return entries


def _sort_entries(entries: list, priority_keywords: list) -> list:
    """
    Sort entries:
      1. Priority: title OR parent path contains a priority keyword → top, newest first
      2. Rest: newest first (mtime DESC)
    """
    priority = [e for e in entries if _is_priority(e['title'] + ' ' + e['parent'], priority_keywords)]
    rest     = [e for e in entries if not _is_priority(e['title'] + ' ' + e['parent'], priority_keywords)]

    priority.sort(key=lambda e: e['mtime'], reverse=True)
    rest.sort(    key=lambda e: e['mtime'], reverse=True)

    return priority + rest


def _build_m3u(entries: list, prefix_parent: bool = True) -> str:
    """Render sorted entries as an M3U string."""
    lines = ['#EXTM3U']
    for e in entries:
        label = f"{e['parent']} {e['title']}" if prefix_parent else e['title']
        lines.append(f"#EXTINF:-1,{label}")
        lines.append(e['path'])
        lines.append('')          # blank line between entries
    return '\n'.join(lines)


def _ensure_playlist_dir():
    """Create playlist output directory if it doesn't exist."""
    real = xbmcvfs.translatePath(PLAYLIST_SAVE_DIR)
    if not xbmcvfs.exists(real):
        xbmcvfs.mkdirs(real)
    return real


def _save_m3u(name: str, content: str) -> str:
    """Write M3U to PLAYLIST_SAVE_DIR/<name>.m3u8  Return full path."""
    out_dir = _ensure_playlist_dir()
    safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')
    path = os.path.join(out_dir, f"{safe_name}.m3u8")
    try:
        f = xbmcvfs.File(path, 'w')
        f.write(content)
        f.close()
        logger.info(f"Playlist saved: {path}")
        return path
    except Exception as e:
        logger.error(f"Save M3U failed: {e}")
        return ''


# ---------------------------------------------------------------------------
# Profile persistence
# ---------------------------------------------------------------------------

def _load_profiles() -> list:
    """Load saved folder profiles from config (JSON list)."""
    raw = config.get_setting(PROFILES_KEY, '[]')
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return []


def _save_profiles(profiles: list):
    config.set_setting(PROFILES_KEY, json.dumps(profiles))


def _get_profile_by_name(name: str) -> dict | None:
    return next((p for p in _load_profiles() if p['name'] == name), None)


def _upsert_profile(profile: dict):
    profiles = _load_profiles()
    idx = next((i for i, p in enumerate(profiles) if p['name'] == profile['name']), None)
    if idx is not None:
        profiles[idx] = profile
    else:
        profiles.append(profile)
    _save_profiles(profiles)


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _dialog_input(heading: str, default: str = '') -> str | None:
    """Show keyboard dialog; return text or None if cancelled."""
    kb = xbmc.Keyboard(default, heading)
    kb.doModal()
    return kb.getText() if kb.isConfirmed() else None


def _pick_folder(heading: str = 'Select folder') -> str | None:
    """Browse for a folder; return path or None."""
    dlg = xbmcgui.Dialog()
    path = dlg.browse(0, heading, 'files', '', False, False, '')
    return path if path else None


def _pick_buckets() -> list:
    """
    Let user multi-select favorites buckets.
    Returns list of {id, name}.
    """
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories ORDER BY sort_order, name")
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Load buckets failed: {e}")
        return []

    if not rows:
        kodi.notify('No favorites buckets found', level='warning')
        return []

    labels = [r[1] for r in rows]
    dlg = xbmcgui.Dialog()
    chosen = dlg.multiselect('Add Favorites Buckets (optional)', labels)
    if not chosen:
        return []
    return [{'id': rows[i][0], 'name': rows[i][1]} for i in chosen]


# ---------------------------------------------------------------------------
# Profile Builder Flow
# ---------------------------------------------------------------------------

def run_profile_builder(existing_profile: dict = None) -> dict | None:
    """
    Interactive wizard to build or edit a playlist profile.
    Returns the completed profile dict, or None if cancelled.

    Profile schema:
    {
      "name": str,
      "folders": [str, ...],           # local or davs:// or smb://
      "buckets": [{"id": int, "name": str}, ...],
      "priority_keywords": [str, ...],
      "prefix_parent": bool,
      "webdav_prefer_local": bool,      # if path also mounted locally, prefer local
      "enabled": bool                   # for Update All
    }
    """
    dlg = xbmcgui.Dialog()

    # --- Profile name ---
    default_name = existing_profile['name'] if existing_profile else ''
    name = _dialog_input('Profile name', default_name)
    if not name:
        return None

    # --- Folder selection loop ---
    folders = list(existing_profile.get('folders', [])) if existing_profile else []

    while True:
        # Show current folders
        current_label = '\n'.join(folders) if folders else '(none yet)'
        options = ['Add local folder', 'Add WebDAV / SMB path (type it)', 'Done']
        if folders:
            options.insert(2, 'Remove a folder')

        choice = dlg.select(
            f'Folders for "{name}" — current:\n{current_label}',
            options
        )

        if choice < 0 or options[choice] == 'Done':
            break
        elif options[choice] == 'Add local folder':
            path = _pick_folder('Select folder to include')
            if path:
                folders.append(path.rstrip('/') + '/')
        elif options[choice] == 'Add WebDAV / SMB path (type it)':
            path = _dialog_input(
                'Enter path (davs://, smb://, or local)',
                'davs://'
            )
            if path:
                folders.append(path.rstrip('/') + '/')
        elif options[choice] == 'Remove a folder':
            if folders:
                rm_idx = dlg.select('Remove which folder?', folders)
                if rm_idx >= 0:
                    folders.pop(rm_idx)

    if not folders:
        # Still allow if buckets will be added
        pass

    # --- Buckets (optional) ---
    add_buckets = dlg.yesno('Favorites Buckets', 'Include favorites bucket(s)?')
    buckets = []
    if add_buckets:
        buckets = _pick_buckets()

    if not folders and not buckets:
        kodi.notify('No sources selected — profile not saved', level='warning')
        return None

    # --- Priority keywords ---
    default_kw = ', '.join(existing_profile.get('priority_keywords', [])) if existing_profile else 'New, Important'
    kw_raw = _dialog_input('Priority keywords (comma-separated)', default_kw)
    priority_keywords = [k.strip() for k in kw_raw.split(',')] if kw_raw else []

    # --- Options ---
    prefix_parent   = dlg.yesno('Display', 'Prepend parent folder name to each title?')
    webdav_pref_loc = dlg.yesno('WebDAV', 'If WebDAV path is also mounted locally, prefer local path?')

    profile = {
        'name':                name,
        'folders':             folders,
        'buckets':             buckets,
        'priority_keywords':   priority_keywords,
        'prefix_parent':       prefix_parent,
        'webdav_prefer_local': webdav_pref_loc,
        'enabled':             existing_profile.get('enabled', True) if existing_profile else True,
    }

    return profile


# ---------------------------------------------------------------------------
# Playlist generation
# ---------------------------------------------------------------------------

def generate_playlist(profile: dict) -> str:
    """
    Scan all sources in a profile, sort, and build M3U.
    Returns the saved file path, or '' on failure.
    """
    all_entries = []

    # --- Folders ---
    for folder in profile.get('folders', []):
        logger.debug(f"Scanning folder: {folder}")
        entries = _scan_folder(folder)

        # WebDAV prefer-local substitution
        if profile.get('webdav_prefer_local') and (
            folder.startswith('davs://') or folder.startswith('smb://')
        ):
            for e in entries:
                # Attempt: strip protocol+host, prepend /storage/emulated/0
                # Only substitute if local path actually exists
                try:
                    parsed = urllib.parse.urlparse(e['path'])
                    local_candidate = parsed.path  # just the path part
                    if xbmcvfs.exists(local_candidate):
                        e['path'] = local_candidate
                except Exception:
                    pass

        all_entries.extend(entries)

    # --- Buckets ---
    for bucket in profile.get('buckets', []):
        bucket_entries = _fetch_bucket_entries(bucket['id'])
        all_entries.extend(bucket_entries)

    if not all_entries:
        kodi.notify(f'No media found for profile "{profile["name"]}"', level='warning')
        return ''

    # --- Sort ---
    sorted_entries = _sort_entries(all_entries, profile.get('priority_keywords', []))

    # --- Build M3U ---
    m3u_content = _build_m3u(sorted_entries, prefix_parent=profile.get('prefix_parent', True))

    # --- Save ---
    path = _save_m3u(profile['name'], m3u_content)
    return path


# ---------------------------------------------------------------------------
# STRM Export (bucket → folder of .strm files)
# ---------------------------------------------------------------------------

def export_bucket_as_strm(bucket_id: int, bucket_name: str):
    """Export a favorites bucket as individual .strm files."""

    dest_folder = _pick_folder(f'Destination folder for "{bucket_name}" STRMs')
    if not dest_folder:
        return

    dest_folder = dest_folder.rstrip('/') + '/'
    # Create subfolder named after bucket
    safe_bucket = re.sub(r'[^\w\s-]', '', bucket_name).strip().replace(' ', '_')
    dest = dest_folder + safe_bucket + '/'
    xbmcvfs.mkdirs(dest)

    entries = _fetch_bucket_entries(bucket_id)
    if not entries:
        kodi.notify('No entries in bucket', level='warning')
        return

    count = 0
    for e in entries:
        fname = re.sub(r'[^\w\s-]', '', e['title'])[:80].strip().replace(' ', '_') + '.strm'
        strm_path = dest + fname
        try:
            f = xbmcvfs.File(strm_path, 'w')
            f.write(e['path'])
            f.close()
            count += 1
        except Exception as ex:
            logger.warning(f"STRM write failed for {fname}: {ex}")

    kodi.notify(f'{count} STRM files exported to {dest}')


# ---------------------------------------------------------------------------
# Update All
# ---------------------------------------------------------------------------

def update_all_profiles():
    """Regenerate M3U for every enabled profile."""
    profiles = _load_profiles()
    enabled  = [p for p in profiles if p.get('enabled', True)]

    if not enabled:
        kodi.notify('No enabled profiles to update', level='warning')
        return

    dlg = xbmcgui.Dialog()
    progress = dlg.progress()
    progress.create('FLUID Playlists', 'Updating playlists...')

    ok = 0
    for i, profile in enumerate(enabled):
        progress.update(
            int((i / len(enabled)) * 100),
            f"[{i+1}/{len(enabled)}] {profile['name']}"
        )
        if progress.iscanceled():
            break
        path = generate_playlist(profile)
        if path:
            ok += 1

    progress.close()
    kodi.notify(f'{ok}/{len(enabled)} playlists updated')


# ---------------------------------------------------------------------------
# Kodi Menu
# ---------------------------------------------------------------------------

def show_playlist_menu():
    """Main playlist menu: profiles + smart lists."""
    import sys
    import xbmcplugin

    addon_handle = int(sys.argv[1]) if len(sys.argv) > 1 else -1
    list_items   = []

    def _item(label, url, is_folder=False, icon='DefaultMusicPlaylists.png'):
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': icon})
        list_items.append((url, li, is_folder))

    base = sys.argv[0]

    # --- Saved profiles ---
    profiles = _load_profiles()
    for p in profiles:
        status = '' if p.get('enabled', True) else ' [OFF]'
        _item(
            f"▶ {p['name']}{status}",
            f"{base}?mode=playlist_run&profile={urllib.parse.quote(p['name'])}",
            is_folder=False
        )

    # --- Management ---
    _item('＋ New Profile',         f"{base}?mode=playlist_new",        icon='DefaultAddSource.png')
    _item('↻ Update All Enabled',   f"{base}?mode=playlist_update_all", icon='DefaultAddonProgram.png')
    _item('⚙ Manage Profiles',      f"{base}?mode=playlist_manage",     icon='DefaultAddonProgram.png')

    # --- Smart lists (favorites-based, kept from original) ---
    gen = SmartPlaylistGenerator()
    for rule_id, rule_info in gen.RULES.items():
        _item(
            f"📋 {rule_info['label']}",
            f"{base}?mode=playlist_smart&rule={rule_id}",
            icon='DefaultMusicPlaylists.png'
        )

    if addon_handle != -1:
        xbmcplugin.addDirectoryItems(addon_handle, list_items)
        xbmcplugin.endOfDirectory(addon_handle)


def handle_playlist_route(params: dict):
    """Dispatcher for all playlist routes — called from router."""
    mode = params.get('mode', '')

    if mode == 'playlist_new':
        profile = run_profile_builder()
        if profile:
            _upsert_profile(profile)
            if xbmcgui.Dialog().yesno('Profile Saved', f'Generate "{profile["name"]}" now?'):
                path = generate_playlist(profile)
                if path:
                    kodi.notify(f'Playlist saved: {os.path.basename(path)}')

    elif mode == 'playlist_run':
        name    = urllib.parse.unquote(params.get('profile', ''))
        profile = _get_profile_by_name(name)
        if profile:
            path = generate_playlist(profile)
            if path:
                kodi.notify(f'Done: {os.path.basename(path)}')
        else:
            kodi.notify(f'Profile "{name}" not found', level='error')

    elif mode == 'playlist_update_all':
        update_all_profiles()

    elif mode == 'playlist_manage':
        _show_manage_profiles()

    elif mode == 'playlist_smart':
        rule = params.get('rule', '')
        gen  = SmartPlaylistGenerator()
        items = gen.generate(rule)
        kodi.notify(f'{len(items)} items in smart list "{rule}"')

    elif mode == 'playlist_main':
        show_playlist_menu()

    elif mode == 'playlist_strm_export':
        bucket_id   = int(params.get('bucket_id', 0))
        bucket_name = params.get('bucket_name', 'Bucket')
        export_bucket_as_strm(bucket_id, bucket_name)


def _show_manage_profiles():
    """Let user edit, toggle, or delete profiles."""
    profiles = _load_profiles()
    if not profiles:
        kodi.notify('No profiles saved yet')
        return

    dlg    = xbmcgui.Dialog()
    labels = []
    for p in profiles:
        state = '✓' if p.get('enabled', True) else '✗'
        labels.append(f"[{state}] {p['name']}")

    idx = dlg.select('Manage Profiles', labels)
    if idx < 0:
        return

    profile = profiles[idx]
    action  = dlg.select(
        profile['name'],
        ['Edit', 'Toggle Enable/Disable', 'Regenerate Now', 'Delete']
    )

    if action == 0:   # Edit
        updated = run_profile_builder(existing_profile=profile)
        if updated:
            _upsert_profile(updated)
            kodi.notify(f'Profile "{updated["name"]}" updated')

    elif action == 1:  # Toggle
        profile['enabled'] = not profile.get('enabled', True)
        _upsert_profile(profile)
        state = 'enabled' if profile['enabled'] else 'disabled'
        kodi.notify(f'"{profile["name"]}" {state}')

    elif action == 2:  # Regenerate
        path = generate_playlist(profile)
        if path:
            kodi.notify(f'Done: {os.path.basename(path)}')

    elif action == 3:  # Delete
        if dlg.yesno('Delete Profile', f'Delete "{profile["name"]}"?'):
            profiles.pop(idx)
            _save_profiles(profiles)
            kodi.notify(f'"{profile["name"]}" deleted')


# ---------------------------------------------------------------------------
# Smart Playlist Generator (kept from original, untouched)
# ---------------------------------------------------------------------------

class SmartPlaylistGenerator:
    """Auto-generate playlists from favorites based on rules."""

    RULES = {
        'recent': {
            'label': 'Recently Added',
            'sql':   'created_at > datetime("now", "-7 days")',
            'order': 'created_at DESC'
        },
        'unwatched': {
            'label': 'Unwatched',
            'sql':   'play_count = 0',
            'order': 'created_at DESC'
        },
        'music': {
            'label': 'Music Videos',
            'sql':   'title LIKE "%music%" OR title LIKE "%song%" OR title LIKE "%audio%"',
            'order': 'title'
        },
        'frequent': {
            'label': 'Most Played',
            'sql':   'play_count > 0',
            'order': 'play_count DESC'
        },
        'long_form': {
            'label': 'Long Videos',
            'sql':   'duration > 1800',
            'order': 'duration DESC'
        }
    }

    def generate(self, rule_name: str, limit: int = 50) -> list:
        if rule_name not in self.RULES:
            return []
        rule = self.RULES[rule_name]
        try:
            conn   = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT video_id, url, title, thumb_url
                FROM favorites
                WHERE {rule['sql']}
                ORDER BY {rule['order']}
                LIMIT ?
            """, (limit,))
            results = cursor.fetchall()
            conn.close()
            return [{'video_id': r[0], 'url': r[1], 'title': r[2], 'thumb': r[3]} for r in results]
        except Exception as e:
            logger.error(f"Smart list generation failed: {e}")
            return []

    def create_combo(self, rules: list, operator: str = 'AND', limit: int = 50) -> list:
        conditions = [self.RULES[r]['sql'] for r in rules if r in self.RULES]
        if not conditions:
            return []
        where = f' {operator} '.join(conditions)
        try:
            conn   = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT video_id, url, title, thumb_url
                FROM favorites
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            results = cursor.fetchall()
            conn.close()
            return [{'video_id': r[0], 'url': r[1], 'title': r[2], 'thumb': r[3]} for r in results]
        except Exception as e:
            logger.error(f"Combo generation failed: {e}")
            return []


# ---------------------------------------------------------------------------
# Module route registration (called by modules/__init__.py auto-discovery)
# ---------------------------------------------------------------------------

MODULE_ROUTES = {
    'playlist_main':       handle_playlist_route,
    'playlist_new':        handle_playlist_route,
    'playlist_run':        handle_playlist_route,
    'playlist_update_all': handle_playlist_route,
    'playlist_manage':     handle_playlist_route,
    'playlist_smart':      handle_playlist_route,
    'playlist_strm_export':handle_playlist_route,
}


__all__ = [
    'show_playlist_menu',
    'handle_playlist_route',
    'MODULE_ROUTES',
    'SmartPlaylistGenerator',
    'generate_playlist',
    'export_bucket_as_strm',
    'update_all_profiles',
]
