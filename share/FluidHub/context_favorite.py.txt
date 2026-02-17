# ruff: noqa: E402
import sys
import os

addon_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(addon_path, 'resources', 'lib'))

from core.config import config
from core.kodi_utils import kodi
from core.logger import logger
import xbmcgui


def main():
    """Dedicated Save to Favorites context entry — no submenu, straight to bucket picker."""
    try:
        video = kodi.get_current_video()
        if not video:
            kodi.notify('Nothing playing or selected', level='warning')
            return
        _add_to_favorite(video)
    except Exception as e:
        logger.error(f"context_favorite error: {e}")


def _add_to_favorite(video):
    """Ask which bucket, save. Falls back to General (id=1) if cancelled."""
    from modules.favorites.manager import FavoritesManager
    from core.database import db

    fm = FavoritesManager()
    category_id = 1

    rows = db.query("""
        SELECT id, name, obfuscated_name, is_private
        FROM categories ORDER BY sort_order, name
    """)

    if rows:
        display_names = []
        for cat_id, name, obfuscated, is_private in rows:
            label = obfuscated if (
                is_private and config.get_setting('obfuscate_private', True)
            ) else name
            display_names.append(f"{'🔒 ' if is_private else ''}{label}")

        choice = xbmcgui.Dialog().select('Save to Favorites', display_names)
        if choice >= 0:
            category_id = rows[choice][0]

    success = fm.add_from_video(video, category_id=category_id)
    if success:
        bucket_label = next(
            (r[2] or r[1] for r in rows if r[0] == category_id),
            'Favorites'
        )
        kodi.notify(f"Saved to {bucket_label}")


if __name__ == '__main__':
    main()
