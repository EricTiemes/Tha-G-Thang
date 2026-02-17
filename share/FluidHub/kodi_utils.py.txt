import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon
from .config import config
from .logger import logger

class ThemeManager:
    """
    Theme manager supporting Default and Chocolate modes
    No module code changes needed - colors applied globally
    """
    
    THEMES = {
        'default': {
            'background': 'FF1F1F1F',
            'text': 'FFE0E0E0',
            'accent': 'FF00BFFF',
            'highlight': 'FF2A2A2A',
            'success': 'FF00FF00',
            'warning': 'FFFFA500',
            'error': 'FFFF0000'
        },
        'chocolate': {
            'background': 'FF2D1B14',      # Dark chocolate
            'text': 'FFD4C4B0',            # Cream
            'accent': 'FF8B4513',          # Saddle brown
            'highlight': 'FF3D241B',       # Lighter chocolate
            'success': 'FF90EE90',
            'warning': 'FFF4A460',
            'error': 'FFCD5C5C'
        }
    }
    
    @classmethod
    def get_color(cls, color_name):
        """Get color hex for current theme"""
        theme = config.theme
        colors = cls.THEMES.get(theme, cls.THEMES['default'])
        return colors.get(color_name, colors['text'])
    
    @classmethod
    def format_text(cls, text, color_name='text', bold=False):
        """Format text with theme color"""
        color = cls.get_color(color_name)
        if bold:
            return f'[B][COLOR {color}]{text}[/COLOR][/B]'
        return f'[COLOR {color}]{text}[/COLOR]'

class KodiUtils:
    """Kodi UI utilities with theme integration"""
    
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self._ = self.addon.getLocalizedString
    
    def notify(self, message, title='FLUID', duration=3000, level='info'):
        """Show themed notification"""
        icon = {
            'info': xbmcgui.NOTIFICATION_INFO,
            'warning': xbmcgui.NOTIFICATION_WARNING,
            'error': xbmcgui.NOTIFICATION_ERROR
        }.get(level, xbmcgui.NOTIFICATION_INFO)
        
        themed_title = ThemeManager.format_text(title, 'accent', bold=True)
        xbmcgui.Dialog().notification(themed_title, message, icon, duration)

    def notify_if_idle(self, message, title='FLUID', duration=3000, level='info'):
        """
        Show notification only when nothing is playing.
        Use for: queue progress, batch updates, background completions.
        Use notify() directly for: errors, user-initiated actions.
        """
        if not xbmc.Player().isPlaying():
            self.notify(message, title, duration, level)
        else:
            logger.debug(f"notify suppressed (playing): {message}")
    
    def dialog_select(self, heading, options, autoclose=0):
        """Themed selection dialog"""
        themed_heading = ThemeManager.format_text(heading, 'accent', bold=True)
        
        dialog = xbmcgui.Dialog()
        choice = dialog.select(themed_heading, options, autoclose=autoclose)
        return choice
    
    def dialog_multiselect(self, heading, options, autoclose=0):
        """Themed multi-select dialog"""
        themed_heading = ThemeManager.format_text(heading, 'accent', bold=True)
        
        dialog = xbmcgui.Dialog()
        selected = dialog.multiselect(themed_heading, options, autoclose=autoclose)
        return selected
    
    def dialog_yesno(self, heading, message, nolabel=None, yeslabel=None):
        """Themed yes/no dialog"""
        themed_heading = ThemeManager.format_text(heading, 'accent', bold=True)
        themed_message = ThemeManager.format_text(message, 'text')
        
        dialog = xbmcgui.Dialog()
        return dialog.yesno(themed_heading, themed_message, nolabel=nolabel, yeslabel=yeslabel)
    
    def dialog_progress(self, heading, message=''):
        """Themed progress dialog"""
        themed_heading = ThemeManager.format_text(heading, 'accent', bold=True)
        
        dialog = xbmcgui.DialogProgress()
        dialog.create(themed_heading, message)
        return dialog
    
    def get_current_video(self):
        """Get currently playing video info from Kodi"""
        try:
            import json
            query = {
                "jsonrpc": "2.0",
                "method": "Player.GetItem",
                "params": {
                    "playerid": 1,
                    "properties": ["file", "title", "thumbnail", "showtitle", "season", "episode"]
                },
                "id": 1
            }
            
            response = xbmc.executeJSONRPC(json.dumps(query))
            data = json.loads(response)
            
            if 'result' in data and 'item' in data['result']:
                item = data['result']['item']
                return {
                    'url': item.get('file'),
                    'title': item.get('title') or item.get('label', 'Unknown'),
                    'thumb': item.get('thumbnail'),
                    'type': item.get('type', 'video')
                }
        except Exception as e:
            logger.error(f"Failed to get current video: {e}")
        
        return None
    
    def get_playlist_items(self):
        """Get current playlist items"""
        try:
            import json
            query = {
                "jsonrpc": "2.0",
                "method": "Playlist.GetItems",
                "params": {
                    "playlistid": 1,
                    "properties": ["title", "file", "thumbnail"]
                },
                "id": 1
            }
            
            response = xbmc.executeJSONRPC(json.dumps(query))
            data = json.loads(response)
            
            if 'result' in data and 'items' in data['result']:
                return data['result']['items']
        except Exception as e:
            logger.error(f"Failed to get playlist: {e}")
        
        return []
    
    def sanitize_filename(self, filename):
        """Clean filename for filesystem"""
        import re
        # Remove invalid characters
        clean = re.sub(r'[\\/*?:"<>|]', '', filename)
        # Limit length
        return clean[:100].strip()
    
    def get_valid_path(self, path):
        """Translate Kodi special paths to real paths"""
        return xbmcvfs.translatePath(path)

# Global utilities instance
kodi = KodiUtils()