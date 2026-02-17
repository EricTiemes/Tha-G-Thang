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
    """Context menu entry point"""
    try:
        items = config.get_context_items()
        if not items:
            return

        # Single item — execute directly, no dialog
        if len(items) == 1:
            execute_action(items[0])
            return

        labels = {
            'quick_download':   'Quick Download',
            'download_options': 'Download with Options...',
            'add_favorite':     'Add to Favorites...',
            'find_extras':      'Find Extras',
        }
        options = [labels.get(i, i) for i in items]
        choice = kodi.dialog_select('FLUID', options)
        if choice >= 0:
            execute_action(items[choice])

    except Exception as e:
        logger.error(f"Context menu error: {e}")


def execute_action(action):
    """Execute selected context action."""
    video = kodi.get_current_video()
    if not video:
        kodi.notify('Nothing playing or selected', level='warning')
        return

    if action in ('quick_download', 'download_options'):
        _execute_download(action, video)

    elif action == 'add_favorite':
        _add_to_favorite(video)

    elif action == 'find_extras':
        from modules.meta.fetcher import MetaFetcher
        MetaFetcher().find_extras_for_video(video)


def _execute_download(action, video):
    """
    Download flow with playing-check.
    1. If playing: ask to stop (Y=stop, N=keep playing)
    2. Either way: confirm start
    3. OK → queue, Cancel → abort
    """
    import xbmc

    player = xbmc.Player()
    if player.isPlaying():
        stop = xbmcgui.Dialog().yesno(
            'FLUID',
            'Video is playing. Stop watching to download?',
            nolabel='Keep Playing',
            yeslabel='Stop'
        )
        if stop:
            player.stop()

    # Either way — confirm download
    confirm = xbmcgui.Dialog().yesno(
        'FLUID',
        f'Start download?\n{video.get("title", "")}',
        nolabel='Cancel',
        yeslabel='Download'
    )
    if not confirm:
        return

    from modules.downloader.engine import FluidDownloader
    dl = FluidDownloader()
    if action == 'download_options':
        dl.download_with_options(video)
    else:
        dl.quick_download(video)


def _add_to_favorite(video):
    """
    Add video to favorites — always asks which bucket.
    Falls back to General (id=1) silently if cancelled or no buckets.
    """
    from modules.favorites.manager import FavoritesManager
    import sqlite3
    from core.database import db

    fm = FavoritesManager()
    category_id = 1   # default fallback

    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, obfuscated_name, is_private
            FROM categories ORDER BY sort_order, name
        """)
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Load buckets failed: {e}")
        rows = []

    if rows:
        display_names = []
        for cat_id, name, obfuscated, is_private in rows:
            label = obfuscated if (
                is_private and config.get_setting('obfuscate_private', True)
            ) else name
            display_names.append(f"{'🔒 ' if is_private else ''}{label}")

        choice = xbmcgui.Dialog().select('Add to bucket', display_names)
        if choice >= 0:
            category_id = rows[choice][0]

    success = fm.add_from_video(video, category_id=category_id)
    if success:
        bucket_label = next(
            (r[2] or r[1] for r in rows if r[0] == category_id),
            'Favorites'
        )
        kodi.notify(f"Added to {bucket_label}")


if __name__ == '__main__':
    main()
