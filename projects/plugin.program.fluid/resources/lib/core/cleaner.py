"""
core/cleaner.py

All text and file cleaning for the addon.

Two separate concerns:
  - Text cleaning  : display titles, filenames, folder names
  - File cleaning  : post-download metadata stripping, old record purge

RULE: URLs are never modified. Any string recognised as a URL
      is returned unchanged by every function here.
"""

import re
import os

from core.intelligence import is_url
from core.logger import logger


# ── Constants ─────────────────────────────────────────────────────────────

_UNSAFE_FS   = re.compile(r'[\\/*?:"<>|]')
_MULTI_SPACE = re.compile(r'\s+')
_EXTENSIONS  = re.compile(r'\.[a-zA-Z0-9]{2,5}$')
_URL_ENCODED = re.compile(r'%[0-9A-Fa-f]{2}')
_MAX_DISPLAY = 200
_MAX_FILENAME = 120
_MAX_FOLDER  = 60


# ── Text cleaning ─────────────────────────────────────────────────────────

def clean_display_title(text: str) -> str:
    """
    Human-readable title for UI labels, M3U entries, notifications.

    - URL → returned unchanged
    - Decode %20 and other percent-encoding
    - Replace _ and - with spaces (where acting as word separators)
    - Strip file extension
    - Collapse whitespace
    - Trim to MAX_DISPLAY chars
    """
    if not text or is_url(text):
        return text

    import urllib.parse
    s = urllib.parse.unquote(text)           # %20 → space etc.
    s = _EXTENSIONS.sub('', s)              # strip .mp4 .mkv etc.
    s = re.sub(r'(?<=[a-z0-9])[-_](?=[a-z0-9])', ' ', s, flags=re.I)
    s = _MULTI_SPACE.sub(' ', s).strip()
    return s[:_MAX_DISPLAY]


def clean_filename(text: str) -> str:
    """
    Filesystem-safe filename (no extension).

    - URL → returned unchanged
    - Unsafe chars removed
    - Spaces → underscores
    - Trim to MAX_FILENAME
    """
    if not text or is_url(text):
        return text

    import urllib.parse
    s = urllib.parse.unquote(text)
    s = _EXTENSIONS.sub('', s)
    s = _UNSAFE_FS.sub('', s)
    s = _MULTI_SPACE.sub(' ', s).strip()
    s = s.replace(' ', '_')
    return s[:_MAX_FILENAME]


def clean_folder_name(text: str) -> str:
    """
    Single path component — no slashes, no dots at start.
    Used for auto-created subfolders from bucket/rule names.

    - URL → returned unchanged
    """
    if not text or is_url(text):
        return text

    s = _UNSAFE_FS.sub('', text)
    s = re.sub(r'[/\\]', '', s)             # no path separators
    s = s.lstrip('.')                        # no leading dots
    s = _MULTI_SPACE.sub(' ', s).strip()
    return s[:_MAX_FOLDER] or '_'           # never empty


def clean_m3u_title(text: str) -> str:
    """
    Clean a title for use in an M3U #EXTINF line.
    Strips extension, decodes percent-encoding, no special chars.
    URL → unchanged (path component in M3U entry, not the title).
    """
    if is_url(text):
        return text
    s = clean_display_title(text)
    # Remove characters that break M3U parsers
    s = re.sub(r'[,\n\r]', ' ', s)
    return s.strip()


# ── File cleaning (post-download) ────────────────────────────────────────

def strip_file_metadata(filepath: str) -> bool:
    """
    Strip embedded metadata/tags from a downloaded file.
    Uses ffmpeg if available, falls back to mutagen for audio.
    Returns True if stripped, False if skipped/failed.
    """
    if not os.path.exists(filepath):
        return False

    ext = os.path.splitext(filepath)[1].lower()

    # Try ffmpeg first (handles video + audio)
    try:
        import subprocess
        tmp = filepath + '.clean' + ext
        result = subprocess.run(
            ['ffmpeg', '-i', filepath, '-map_metadata', '-1',
             '-c:v', 'copy', '-c:a', 'copy', '-y', tmp],
            capture_output=True, timeout=120
        )
        if result.returncode == 0 and os.path.exists(tmp):
            os.replace(tmp, filepath)
            logger.debug(f"Metadata stripped via ffmpeg: {filepath}")
            return True
        if os.path.exists(tmp):
            os.remove(tmp)
    except (FileNotFoundError, Exception):
        pass  # ffmpeg not available

    # Audio fallback via mutagen
    if ext in ('.mp3', '.m4a', '.flac', '.ogg', '.opus'):
        try:
            import mutagen
            f = mutagen.File(filepath)
            if f is not None:
                f.delete()
                f.save()
                logger.debug(f"Tags removed via mutagen: {filepath}")
                return True
        except Exception:
            pass

    logger.debug(f"strip_file_metadata: no tool available for {ext}")
    return False


# ── Database maintenance ──────────────────────────────────────────────────

def purge_old_records(days_downloads: int = 30,
                      days_delivery: int = 7) -> dict:
    """
    Remove old completed records from downloads and delivery_queue.
    Called by service.py on hourly tick.
    Returns counts of rows deleted.
    """
    from core.database import db
    counts = {'downloads': 0, 'delivery': 0}

    try:
        deleted = db.execute("""
            DELETE FROM downloads
            WHERE status IN ('completed','failed')
            AND created_at < datetime('now', ?)
        """, (f'-{days_downloads} days',))
        counts['downloads'] = deleted

        deleted = db.execute("""
            DELETE FROM delivery_queue
            WHERE status IN ('delivered','failed')
            AND created_at < datetime('now', ?)
        """, (f'-{days_delivery} days',))
        counts['delivery'] = deleted

        logger.debug(f"Purge: {counts}")
    except Exception as e:
        logger.error(f"purge_old_records failed: {e}")

    return counts


__all__ = [
    'clean_display_title',
    'clean_filename',
    'clean_folder_name',
    'clean_m3u_title',
    'strip_file_metadata',
    'purge_old_records',
]
