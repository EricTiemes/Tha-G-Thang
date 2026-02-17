"""
core/intelligence.py

Pattern-matching and classification for the addon.
No preset categories — learns from the user's own bucket names,
folder names, and delivery rules.

Safe rule: never modifies URLs. Any string starting with a known
protocol is returned unchanged by all cleaning functions.
"""

import re
import os
import time
import urllib.parse


# ── URL safety ────────────────────────────────────────────────────────────

_URL_SCHEMES = ('http://', 'https://', 'plugin://', 'davs://', 'smb://',
                'nfs://', 'ftp://', 'special://', 'rtmp://', 'rtsp://')

def is_url(s: str) -> bool:
    """True if string is a URL that must never be modified."""
    return s.lower().startswith(_URL_SCHEMES)


# ── Platform detection ────────────────────────────────────────────────────

_SOURCE_PATTERNS = [
    (r'youtube\.com|youtu\.be',    'youtube'),
    (r'vimeo\.com',                'vimeo'),
    (r'dailymotion\.com',          'dailymotion'),
    (r'twitch\.tv',                'twitch'),
    (r'soundcloud\.com',           'soundcloud'),
    (r'bandcamp\.com',             'bandcamp'),
    (r'reddit\.com|redd\.it',      'reddit'),
    (r'twitter\.com|x\.com',       'twitter'),
    (r'instagram\.com',            'instagram'),
    (r'tiktok\.com',               'tiktok'),
    (r'rumble\.com',               'rumble'),
    (r'odysee\.com|lbry\.tv',      'odysee'),
    (r'facebook\.com|fb\.watch',   'facebook'),
]

def source_from_url(url: str) -> str:
    """Return platform name or 'unknown'."""
    lower = url.lower()
    for pattern, name in _SOURCE_PATTERNS:
        if re.search(pattern, lower):
            return name
    return 'unknown'


# ── Video ID extraction ───────────────────────────────────────────────────

_VIDEO_ID_PATTERNS = [
    r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})',
    r'vimeo\.com/(\d{6,12})',
    r'dailymotion\.com/video/([a-z0-9]+)',
    r'twitch\.tv/videos/(\d+)',
    r'/([A-Za-z0-9_-]{8,16})(?:\?|$)',
]

def video_id_from_url(url: str) -> str:
    """Extract canonical video ID; falls back to stable hash."""
    for pattern in _VIDEO_ID_PATTERNS:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    parsed = urllib.parse.urlparse(url)
    return str(abs(hash(parsed.netloc + parsed.path)) % 10_000_000)


# ── User-vocabulary classification ───────────────────────────────────────

def _load_user_vocabulary() -> dict:
    """
    Build vocabulary from user's bucket names, folder names,
    and delivery rule names. Called at classification time so it
    always reflects current settings without restart.

    Returns dict: {keyword_lower: {'bucket': str, 'folder': str}}
    """
    vocab = {}
    try:
        from core.config import config
        from core.database import db
        import sqlite3

        # Bucket names → keywords
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, obfuscated_name, is_private FROM categories")
        for name, obfuscated, is_private in cursor.fetchall():
            # Never index private/obfuscated bucket names as keywords
            if is_private and obfuscated:
                continue
            for word in re.split(r'\W+', name.lower()):
                if len(word) > 2:
                    vocab[word] = {'bucket': name, 'folder': name}
        conn.close()

        # Delivery rule names and keywords
        for rule in config.get_delivery_rules():
            rule_name = rule.get('name', '')
            for kw in rule.get('keywords', []):
                kw_lower = kw.lower().strip()
                if kw_lower:
                    vocab[kw_lower] = {
                        'bucket': rule_name,
                        'folder': rule_name,
                    }

    except Exception:
        pass  # No DB yet on first run — return empty vocab
    return vocab


def classify_content(title: str, url: str = '',
                     meta: dict = None) -> dict:
    """
    Classify a video using the user's own vocabulary.

    Checks (in order):
      1. YouTube categories/tags from meta (most reliable)
      2. User bucket/rule keywords vs title + tags
      3. Source platform boosts

    Returns:
        {
            'bucket':     str | None,   # suggested favorites bucket
            'folder':     str | None,   # suggested subfolder (None for private)
            'confidence': int,          # 0–100
            'source':     str,
            'is_private': bool,
        }
    """
    source = source_from_url(url)
    text   = title.lower()
    meta   = meta or {}

    # Enrich text with YouTube meta if available
    yt_tags       = ' '.join(meta.get('tags', [])).lower()
    yt_categories = ' '.join(meta.get('categories', [])).lower()
    full_text     = f"{text} {yt_tags} {yt_categories}"

    vocab   = _load_user_vocabulary()
    best    = None
    score   = 0

    for keyword, mapping in vocab.items():
        if keyword in full_text:
            hit_score = 10
            # Exact word match scores higher than substring
            if re.search(rf'\b{re.escape(keyword)}\b', full_text):
                hit_score = 20
            if hit_score > score:
                score = hit_score
                best  = mapping

    # Platform boosts
    if source == 'soundcloud' and not best:
        best  = {'bucket': 'Music Videos', 'folder': 'Music Videos'}
        score = 15
    if source == 'twitch' and not best:
        best  = {'bucket': 'Clips', 'folder': 'Clips'}
        score = 15

    if best:
        return {
            'bucket':     best['bucket'],
            'folder':     best['folder'],
            'confidence': min(score, 100),
            'source':     source,
            'is_private': False,
        }

    # No match — return unknown, caller decides fallback
    return {
        'bucket':     None,
        'folder':     None,
        'confidence': 0,
        'source':     source,
        'is_private': False,
    }


# ── Discrete/private naming templates ────────────────────────────────────

_DISCRETE_PRESETS = ['_', '__', 'custom']

def apply_discrete_template(name: str, template: str) -> str:
    """
    Apply a discrete naming template to a bucket or folder name.

    template='_'    → '_'         (single underscore, hides name)
    template='__'   → '__'        (double underscore)
    template='custom' → name      (user types their own in settings)
    any other value → that value  (user-defined literal)
    """
    if template in ('_', '__'):
        return template
    if template == 'custom' or not template:
        return name   # fall back to real name if no custom value set
    return template   # literal user-defined value


def suggest_discrete_folder(base_path: str, template: str) -> str:
    """
    Build a discrete subfolder path using template.
    base_path/template/  e.g.  /downloads/clips/__/
    Never exposes content type in the path.
    """
    segment = apply_discrete_template('', template) or '_'
    return os.path.join(base_path.rstrip('/'), segment) + '/'


# ── Filename and folder building ─────────────────────────────────────────

def build_filename(title: str, privacy_mode: bool = False,
                   ext: str = '') -> str:
    """
    Build clean filesystem filename.
    privacy_mode=True → unix timestamp only, no title info.
    Never call on URLs.
    """
    if privacy_mode:
        return str(int(time.time())) + ext
    from core.cleaner import clean_filename
    return clean_filename(title) + ext


def build_folder_structure(info: dict, base_path: str,
                           use_source: bool = True,
                           use_type: bool = True) -> str:
    """
    Suggest a folder path from classification.
    base_path/[Source]/[Folder]/
    Private content: caller must pass discrete template separately.
    """
    parts = [base_path.rstrip('/')]
    if use_source and info.get('source', 'unknown') != 'unknown':
        parts.append(info['source'].capitalize())
    if use_type and info.get('folder'):
        parts.append(info['folder'])
    return os.path.join(*parts) + '/'


# ── Delivery path suggestion ──────────────────────────────────────────────

def suggest_delivery_paths(video_info: dict, rules: list,
                           meta: dict = None) -> list:
    """
    Match delivery rules against video using classification.
    Returns ordered list of destination dicts.
    First matching rule wins. Falls back to first rule if no match.
    """
    title  = video_info.get('title', '')
    url    = video_info.get('url', '')
    info   = classify_content(title, url, meta=meta)

    text = (title + ' ' + (info.get('folder') or '') +
            ' ' + info['source']).lower()

    for rule in rules:
        keywords = rule.get('keywords', [])
        if any(kw.lower() in text for kw in keywords):
            return [{
                'path':     path,
                'protocol': rule.get('protocol', 'local'),
                'name':     rule.get('name', 'Unknown'),
            } for path in rule.get('paths', [])]

    # Fallback
    if rules:
        first = rules[0]
        return [{
            'path':     path,
            'protocol': first.get('protocol', 'local'),
            'name':     first.get('name', 'Default'),
        } for path in first.get('paths', []) if path]

    return []


# ── YouTube meta fields to persist ───────────────────────────────────────

YT_META_FIELDS = [
    'channel', 'channel_id', 'uploader',
    'upload_date',           # YYYYMMDD string
    'duration',              # seconds
    'view_count',            # for local popularity sort
    'tags',                  # list — feeds classify_content()
    'categories',            # list — YouTube's own classification
    'description',           # truncated to 300 chars on save
    'playlist_title',        # grouping if downloaded from playlist
    'playlist_id',
    'thumbnail',             # best available URL
]

def extract_yt_meta(ydl_info: dict) -> dict:
    """
    Extract the fields worth persisting from a yt-dlp info dict.
    Truncates description. Safe to call with any dict.
    """
    out = {}
    for field in YT_META_FIELDS:
        val = ydl_info.get(field)
        if val is None:
            continue
        if field == 'description' and isinstance(val, str):
            val = val[:300]
        out[field] = val
    return out


__all__ = [
    'is_url',
    'source_from_url',
    'video_id_from_url',
    'classify_content',
    'build_filename',
    'build_folder_structure',
    'suggest_delivery_paths',
    'suggest_discrete_folder',
    'apply_discrete_template',
    'extract_yt_meta',
    'YT_META_FIELDS',
    '_DISCRETE_PRESETS',
]
