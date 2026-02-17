import os
import random
import string
import xbmcvfs
import xbmc

from core.config import config
from core.database import db
from core.kodi_utils import kodi
from core.logger import logger

class FavoritesManager:
    """
    Complete favorites management
    - Categories/buckets with privacy obfuscation
    - Import from SuperFavourites and other addons
    - Export to STRM, M3U, JSON
    """
    
    def __init__(self):
        self.db = db
    
    def create_category(self, name, is_private=False, icon=None):
        """
        Create new category/bucket
        Private buckets get obfuscated names
        """
        obfuscated = None
        display_name = name
        
        if is_private and config.get_setting('obfuscate_private', True):
            # Generate random obfuscated name
            obfuscated = ''.join(random.choices(
                string.ascii_lowercase + string.digits, k=12
            ))
            display_name = f"Bucket_{obfuscated[:4]}"
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO categories (name, obfuscated_name, is_private, icon)
                VALUES (?, ?, ?, ?)
            """, (name, obfuscated, is_private, icon))
            
            cat_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return cat_id, display_name
            
        except Exception as e:
            logger.error(f"Failed to create category: {e}")
            return None, name
    
    def add_from_video(self, video_info, category_id=1, privacy_mode=False):
        """Add current video to favorites"""
        video_id = self._extract_video_id(video_info['url'])
        
        # Extract source addon from URL
        source = self._detect_source(video_info['url'])
        
        success = self.db.add_favorite(
            video_id=video_id,
            url=video_info['url'],
            title=video_info['title'],
            thumb_url=video_info.get('thumb'),
            category_id=category_id,
            source_addon=source,
            privacy_mode=privacy_mode
        )
        
        if success:
            kodi.notify(f'Added: {video_info["title"][:30]}...')
        
        return success
    
    def import_from_superfavourites(self, sf_path=None):
        """
        Import from Super Favourites folder structure
        sf_path: path to SuperFavourites database or folder
        """
        if not sf_path:
            # Default location
            sf_path = xbmcvfs.translatePath('special://profile/addon_data/plugin.program.super.favourites')
        
        imported = 0
        
        try:
            # Parse SuperFavourites structure
            import xml.etree.ElementTree as ET
            
            fav_file = os.path.join(sf_path, 'favourites.xml')
            if not os.path.exists(fav_file):
                kodi.notify('SuperFavourites not found', level='warning')
                return 0
            
            tree = ET.parse(fav_file)
            root = tree.getroot()
            
            for fav in root.findall('.//favourite'):
                name = fav.get('name', 'Unknown')
                url = fav.get('url', '')
                thumb = fav.get('thumb', '')
                
                if not url:
                    continue
                
                video_id = self._extract_video_id(url)
                source = self._detect_source(url)
                
                self.db.add_favorite(
                    video_id=video_id,
                    url=url,
                    title=name,
                    thumb_url=thumb,
                    source_addon=source
                )
                imported += 1
            
            kodi.notify(f'Imported {imported} favorites')
            
        except Exception as e:
            logger.error(f"Import error: {e}")
            kodi.notify('Import failed', level='error')
        
        return imported
    
    def export_to_strm(self, category_id=None, output_path=None):
        """
        Export favorites as STRM files
        Creates .strm files that Kodi can play directly
        """
        if not output_path:
            output_path = kodi.get_valid_path('special://profile/FLUID_Export')
        
        if not xbmcvfs.exists(output_path):
            xbmcvfs.mkdirs(output_path)
        
        favorites = self.db.get_favorites(category_id=category_id)
        
        for video_id, url, title, thumb, created in favorites:
            # Sanitize filename
            safe_name = kodi.sanitize_filename(title or video_id)
            strm_path = os.path.join(output_path, f"{safe_name}.strm")
            
            # Write STRM file (just the URL)
            with xbmcvfs.File(strm_path, 'w') as f:
                f.write(url)
        
        kodi.notify(f'Exported {len(favorites)} items to STRM')
        return len(favorites)
    
    def export_to_m3u(self, category_id=None, output_path=None):
        """Export as M3U playlist"""
        if not output_path:
            output_path = kodi.get_valid_path('special://profile/FLUID_Playlist.m3u')

        favorites = self.db.get_favorites(category_id=category_id)

        with xbmcvfs.File(output_path, 'w') as f:
            f.write('#EXTM3U\n')
            for video_id, url, title, thumb, created in favorites:
                f.write(f'#EXTINF:-1,{title}\n')
                f.write(f'{url}\n')

        kodi.notify(f'Exported {len(favorites)} items to M3U')
        return len(favorites)

    def export_to_json(self, category_id=None, output_path=None):
        """Export favorites as JSON — useful for backup/migration"""
        import json as _json
        if not output_path:
            output_path = kodi.get_valid_path('special://profile/FLUID_Export.json')

        favorites = self.db.get_favorites(category_id=category_id)

        data = [
            {'video_id': r[0], 'url': r[1], 'title': r[2],
             'thumb_url': r[3], 'created_at': r[4]}
            for r in favorites
        ]

        try:
            with xbmcvfs.File(output_path, 'w') as f:
                f.write(_json.dumps(data, indent=2, ensure_ascii=False))
            kodi.notify(f'Exported {len(data)} items to JSON')
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            kodi.notify('Export failed', level='error')

        return len(data)
    
    def get_categories(self, include_private=True):
        """Get all categories"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            if include_private:
                cursor.execute("""
                    SELECT id, name, obfuscated_name, is_private, icon
                    FROM categories ORDER BY sort_order
                """)
            else:
                cursor.execute("""
                    SELECT id, name, obfuscated_name, is_private, icon
                    FROM categories WHERE is_private=0 ORDER BY sort_order
                """)
            
            results = cursor.fetchall()
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return []
    
    def _extract_video_id(self, url):
        """Extract video ID from URL"""
        import re
        match = re.search(r'(?:v=|/)([\w-]{11})', url)
        return match.group(1) if match else str(hash(url) % 10000000)
    
    def _detect_source(self, url):
        """Detect source addon from URL"""
        if 'youtube' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'vimeo' in url:
            return 'vimeo'
        elif 'dailymotion' in url:
            return 'dailymotion'
        elif 'twitch' in url:
            return 'twitch'
        return 'unknown'

class SmartListGenerator:
    """Auto-generate playlists from favorites based on rules"""
    
    RULES = {
        'recent': {
            'label': 'Recently Added',
            'sql': 'created_at > datetime("now", "-7 days")',
            'order': 'created_at DESC'
        },
        'unwatched': {
            'label': 'Unwatched',
            'sql': 'play_count = 0',
            'order': 'created_at DESC'
        },
        'music': {
            'label': 'Music Videos',
            'sql': 'title LIKE "%music%" OR title LIKE "%song%" OR title LIKE "%audio%"',
            'order': 'title'
        },
        'frequent': {
            'label': 'Most Played',
            'sql': 'play_count > 0',
            'order': 'play_count DESC'
        }
    }
    
    def generate(self, rule_name, limit=50):
        """Generate playlist from rule"""
        if rule_name not in self.RULES:
            return []
        
        rule = self.RULES[rule_name]
        
        try:
            import sqlite3
            conn = sqlite3.connect(db.db_path)
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
            
            return [{
                'video_id': r[0],
                'url': r[1],
                'title': r[2],
                'thumb': r[3]
            } for r in results]
            
        except Exception as e:
            logger.error(f"Smart list generation failed: {e}")
            return []

def show_favorites_menu():
    """Build favorites menu for Kodi UI"""
    import sys
    import xbmcplugin
    import xbmcgui
    
    addon_handle = int(sys.argv[1])
    
    manager = FavoritesManager()
    categories = manager.get_categories()
    
    list_items = []
    
    # Smart lists
    gen = SmartListGenerator()
    for rule_id, rule_info in gen.RULES.items():
        item = xbmcgui.ListItem(label=f"📋 {rule_info['label']}")
        item.setArt({'icon': 'DefaultMusicPlaylists.png'})
        url = f"{sys.argv[0]}?mode=favorites_smart&rule={rule_id}"
        list_items.append((url, item, True))
    
    # Categories
    for cat_id, name, obfuscated, is_private, icon in categories:
        display_name = obfuscated if (is_private and config.get_setting('obfuscate_private', True)) else name
        icon_img = 'DefaultFolder.png' if not is_private else 'DefaultLock.png'
        
        item = xbmcgui.ListItem(label=f"📁 {display_name}")
        item.setArt({'icon': icon_img})
        url = f"{sys.argv[0]}?mode=favorites_category&id={cat_id}"
        list_items.append((url, item, True))
    
    # Actions
    item = xbmcgui.ListItem(label="➕ New Category...")
    item.setArt({'icon': 'DefaultAddSource.png'})
    url = f"{sys.argv[0]}?mode=favorites_new_cat"
    list_items.append((url, item, False))
    
    item = xbmcgui.ListItem(label="📥 Import...")
    item.setArt({'icon': 'DefaultAddonProgram.png'})
    url = f"{sys.argv[0]}?mode=favorites_import"
    list_items.append((url, item, False))
    
    item = xbmcgui.ListItem(label="📤 Export...")
    item.setArt({'icon': 'DefaultAddonProgram.png'})
    url = f"{sys.argv[0]}?mode=favorites_export"
    list_items.append((url, item, False))
    
    xbmcplugin.addDirectoryItems(addon_handle, list_items)
    xbmcplugin.endOfDirectory(addon_handle)



# ---------------------------------------------------------------------------
# Module route registration
# ---------------------------------------------------------------------------

def _handle_favorites_route(params):
    """Dispatcher for all favorites routes."""
    mode = params.get('mode', '')
    if mode == 'favorites_main':
        show_favorites_menu()
    elif mode == 'favorites_category':
        _show_category(int(params.get('id', 1)))
    elif mode == 'favorites_new_cat':
        _new_category_dialog()
    elif mode == 'favorites_import':
        _import_dialog()
    elif mode == 'favorites_export':
        _export_dialog()


def _show_category(cat_id):
    import sys
    import xbmcgui
    import xbmcplugin
    addon_handle = int(sys.argv[1]) if len(sys.argv) > 1 else -1
    items = db.get_favorites(category_id=cat_id)
    list_items = []
    for video_id, url, title, thumb, created_at in items:
        li = xbmcgui.ListItem(label=title or url, label2=created_at or '')
        li.setArt({'thumb': thumb or '', 'icon': 'DefaultVideo.png'})
        li.setInfo('video', {'title': title})
        list_items.append((url, li, False))
    if not list_items:
        li = xbmcgui.ListItem(label='No items in this bucket')
        list_items.append((sys.argv[0], li, False))
    if addon_handle != -1:
        xbmcplugin.addDirectoryItems(addon_handle, list_items)
        xbmcplugin.endOfDirectory(addon_handle)


def _new_category_dialog():
    import xbmc
    kb = xbmc.Keyboard('', 'New bucket name')
    kb.doModal()
    if not kb.isConfirmed():
        return
    name = kb.getText().strip()
    if name:
        is_private = kodi.dialog_yesno('Privacy', f'Make "{name}" a private bucket?')
        FavoritesManager().create_category(name, is_private=is_private)
        kodi.notify(f'Bucket "{name}" created')


def _import_dialog():
    FavoritesManager().import_from_superfavourites()


def _export_dialog():
    """Let user pick a bucket then export it."""
    import sqlite3
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories ORDER BY sort_order, name")
        rows = cursor.fetchall()
        conn.close()
    except Exception:
        rows = []
    if not rows:
        kodi.notify('No buckets to export', level='warning')
        return
    import xbmcgui
    choice = xbmcgui.Dialog().select('Export which bucket?', [r[1] for r in rows])
    if choice < 0:
        return
    cat_id, cat_name = rows[choice]
    fmt = xbmcgui.Dialog().select('Export format', ['M3U', 'STRM files', 'JSON'])
    if fmt < 0:
        return
    fm = FavoritesManager()
    if fmt == 0:
        fm.export_to_m3u(cat_id)
    elif fmt == 1:
        fm.export_to_strm(cat_id)
    elif fmt == 2:
        fm.export_to_json(cat_id)


MODULE_ROUTES = {
    'favorites_main':     _handle_favorites_route,
    'favorites_category': _handle_favorites_route,
    'favorites_new_cat':  _handle_favorites_route,
    'favorites_import':   _handle_favorites_route,
    'favorites_export':   _handle_favorites_route,
}

__all__ = ['FavoritesManager', 'SmartListGenerator', 'show_favorites_menu', 'MODULE_ROUTES']