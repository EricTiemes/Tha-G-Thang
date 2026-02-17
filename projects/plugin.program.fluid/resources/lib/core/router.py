import sys
import urllib.parse
from .logger import logger

class RouteDispatcher:
    """
    URL Router for handling different addon modes
    Supports: plugin://, script://, service://
    """
    
    def __init__(self):
        self.routes = {}
        self.module_routes = {}
    
    def route(self, path):
        """Decorator to register route"""
        def decorator(func):
            self.routes[path] = func
            return func
        return decorator
    
    def register_module_routes(self, module_id, routes_dict):
        """Register routes from a module"""
        self.module_routes[module_id] = routes_dict
    
    def dispatch(self, url_string):
        """Parse URL and dispatch to handler"""
        if not url_string:
            return self._show_main_menu()
        
        try:
            # Parse URL parameters
            params = dict(urllib.parse.parse_qsl(url_string))
            mode = params.get('mode', 'main')
            
            logger.debug(f"Routing: mode={mode}, params={params}")
            
            # Check core routes
            if mode in self.routes:
                return self.routes[mode](params)
            
            # Check module routes
            for module_id, routes in self.module_routes.items():
                if mode in routes:
                    return routes[mode](params)
            
            # Default: main menu
            return self._show_main_menu()
            
        except Exception as e:
            logger.error(f"Routing error: {e}")
            return self._show_main_menu()
    
    def _show_main_menu(self):
        """Build and show main menu based on enabled modules"""
        from .config import config
        from .kodi_utils import ThemeManager
        import xbmcgui
        import xbmcplugin
        
        addon_handle = int(sys.argv[1]) if len(sys.argv) > 1 else -1
        
        list_items = []
        
        # Always show Download Current if downloader enabled
        if config.is_module_enabled('downloader'):
            item = xbmcgui.ListItem(
                label=ThemeManager.format_text('Download Current', 'accent', bold=True)
            )
            item.setArt({'icon': 'DefaultVideo.png'})
            url = f"{sys.argv[0]}?mode=download_current"
            list_items.append((url, item, True))
        
        # Queue Manager
        if config.is_module_enabled('downloader'):
            item = xbmcgui.ListItem(label='Queue Manager')
            item.setArt({'icon': 'DefaultFolder.png'})
            url = f"{sys.argv[0]}?mode=queue_manager"
            list_items.append((url, item, True))
        
        # Favorites
        if config.is_module_visible('favorites'):
            item = xbmcgui.ListItem(label='My Favorites')
            item.setArt({'icon': 'DefaultFavourites.png'})
            url = f"{sys.argv[0]}?mode=favorites_main"
            list_items.append((url, item, True))
        
        # Playlist
        if config.is_module_visible('playlist'):
            item = xbmcgui.ListItem(label='Smart Playlists')
            item.setArt({'icon': 'DefaultMusicPlaylists.png'})
            url = f"{sys.argv[0]}?mode=playlist_main"
            list_items.append((url, item, True))
        
        # Metadata
        if config.is_module_visible('meta'):
            item = xbmcgui.ListItem(label='Metadata Tools')
            item.setArt({'icon': 'DefaultAddonInfoProvider.png'})
            url = f"{sys.argv[0]}?mode=meta_main"
            list_items.append((url, item, True))
        
        # Settings
        item = xbmcgui.ListItem(label='Settings')
        item.setArt({'icon': 'DefaultAddonProgram.png'})
        url = f"{sys.argv[0]}?mode=settings"
        list_items.append((url, item, False))
        
        if addon_handle != -1:
            xbmcplugin.addDirectoryItems(addon_handle, list_items)
            xbmcplugin.endOfDirectory(addon_handle)
        
        return list_items

# Global router instance
router = RouteDispatcher()

# Core routes
@router.route('download_current')
def route_download_current(params):
    """Handle download current video"""
    from modules.downloader.engine import FluidDownloader
    dl = FluidDownloader()
    dl.quick_download()

@router.route('queue_manager')
def route_queue_manager(params):
    """Show recent downloads from DB — simple inline view, no separate module needed"""
    import xbmcgui
    import xbmcplugin
    from core.database import db

    addon_handle = int(sys.argv[1]) if len(sys.argv) > 1 else -1
    list_items = []

    STATUS_ICON = {
        'queued':    ('⏳', 'DefaultAddonProgram.png'),
        'running':   ('⬇', 'DefaultVideo.png'),
        'completed': ('✅', 'DefaultVideoPlaylists.png'),
        'failed':    ('❌', 'DefaultAddonProgram.png'),
    }

    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT title, status, quality, created_at, error_msg
            FROM downloads
            ORDER BY created_at DESC LIMIT 50
        """)
        rows = cursor.fetchall()
        conn.close()
    except Exception:
        rows = []

    if not rows:
        item = xbmcgui.ListItem(label='No downloads yet')
        list_items.append((sys.argv[0], item, False))
    else:
        for title, status, quality, created_at, error_msg in rows:
            icon_char, icon_img = STATUS_ICON.get(status, ('•', 'DefaultVideo.png'))
            label = f"{icon_char}  {title or 'Unknown'}  [{quality or '?'}]"
            sublabel = error_msg if status == 'failed' else (created_at or '')
            item = xbmcgui.ListItem(label=label, label2=sublabel)
            item.setArt({'icon': icon_img})
            list_items.append((sys.argv[0], item, False))

    if addon_handle != -1:
        xbmcplugin.addDirectoryItems(addon_handle, list_items)
        xbmcplugin.endOfDirectory(addon_handle)

@router.route('download_options')
def route_download_options(params):
    from modules.downloader.engine import FluidDownloader
    dl = FluidDownloader()
    dl.download_with_options()

@router.route('settings')
def route_settings(params):
    """Open settings"""
    import xbmcaddon
    xbmcaddon.Addon().openSettings()

@router.route('favorites_main')
def route_favorites(params):
    """Favorites main menu"""
    from modules.favorites.manager import show_favorites_menu
    show_favorites_menu()

@router.route('playlist_main')
def route_playlist(params):
    """Playlist main menu"""
    from modules.playlist.builder import handle_playlist_route
    handle_playlist_route(params)

@router.route('meta_main')
def route_meta(params):
    """Metadata main menu"""
    from modules.meta.fetcher import show_meta_menu
    show_meta_menu()

@router.route('setup_wizard')
def route_setup_wizard(params):
    """Re-run first-run wizard from Settings action button"""
    from core.config import config
    config.set_setting('first_run', True)
    import xbmc
    xbmc.executebuiltin('RunPlugin(plugin://plugin.video.fluid/)')

