import xbmcvfs
import xbmcaddon
import json
import os

class FluidConfig:
    """
    Three-tier configuration manager
    Simple -> Advanced -> Pro/Dev modes
    """
    
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.addon_id = self.addon.getAddonInfo('id')
        self.profile_path = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        
        # Ensure profile directory exists
        if not os.path.exists(self.profile_path):
            os.makedirs(self.profile_path)
    
    def get_setting(self, setting_id, default=None):
        """Get setting value with type detection"""
        try:
            value = self.addon.getSetting(setting_id)
            
            # Try JSON parsing for complex values
            if value.startswith('[') or value.startswith('{'):
                try:
                    return json.loads(value)
                except Exception:
                    pass
            
            # Boolean detection
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            
            # Integer detection
            try:
                return int(value)
            except Exception:
                pass
            
            # Float detection
            try:
                return float(value)
            except Exception:
                pass
            
            return value if value else default
        except Exception:
            return default
    
    def set_setting(self, setting_id, value):
        """Set setting value"""
        if isinstance(value, (list, dict)):
            value = json.dumps(value)
        elif isinstance(value, bool):
            value = 'true' if value else 'false'
        else:
            value = str(value)
        
        self.addon.setSetting(setting_id, value)
    
    @property
    def settings_mode(self):
        """Current settings mode: simple, advanced, pro"""
        return self.get_setting('settings_mode', 'simple')
    
    @property
    def theme(self):
        """Current theme: default or chocolate"""
        return self.get_setting('theme', 'default')
    
    @property
    def is_simple_mode(self):
        return self.settings_mode == 'simple'
    
    @property
    def is_advanced_mode(self):
        return self.settings_mode in ('advanced', 'pro')
    
    @property
    def is_pro_mode(self):
        return self.settings_mode == 'pro'
    
    # Flow control properties
    @property
    def download_mode(self):
        """background or manual"""
        if self.is_simple_mode:
            return 'background'
        return self.get_setting('adv_download_mode', 'background')
    
    @property
    def delivery_mode(self):
        """background, manual, or ask"""
        if self.is_simple_mode:
            return 'background' if self.get_setting('simple_auto_deliver', True) else 'manual'
        return self.get_setting('adv_delivery_mode', 'background')
    
    @property
    def show_progress(self):
        if self.is_simple_mode:
            return self.get_setting('simple_background_progress', True)
        return True
    
    # Privacy settings
    @property
    def privacy_timestamp_rename(self):
        return self.get_setting('privacy_timestamp_rename', False) if self.is_advanced_mode else False
    
    @property
    def privacy_strip_exif(self):
        return self.get_setting('privacy_strip_exif', False) if self.is_advanced_mode else False
    
    @property
    def privacy_minimal_meta(self):
        return self.get_setting('privacy_minimal_meta', True) if self.is_advanced_mode else True
    
    # Context menu configuration
    def get_context_items(self):
        """Get enabled context menu items based on settings"""
        if self.is_simple_mode:
            return ['quick_download']
        
        items = []
        if self.get_setting('context_quick_download', True):
            items.append('quick_download')
        if self.get_setting('context_download_options', True):
            items.append('download_options')
        if self.get_setting('context_add_favorite', False):
            items.append('add_favorite')
        if self.get_setting('context_find_extras', False):
            items.append('find_extras')
        
        max_items = self.get_setting('context_max_items', 3)
        return items[:max_items]
    
    # Module visibility
    # Core modules that should be on by default
    _CORE_MODULES = {'downloader', 'delivery'}

    def is_module_enabled(self, module_id):
        """Check if module is enabled — core modules default True"""
        default = module_id in self._CORE_MODULES
        return self.get_setting(f'module_{module_id}', default)
    
    def is_module_visible(self, module_id):
        """Check if module should show in menu"""
        enabled = self.is_module_enabled(module_id)
        visible = self.get_setting(f'module_{module_id}_menu', True)
        return enabled and visible
    
    # Delivery rules
    def get_delivery_rules(self):
        """Get delivery routing rules"""
        default_rules = [
            {
                "name": "Music",
                "keywords": ["music", "song", "audio", "mp3"],
                "paths": ["special://profile/Music"],
                "protocol": "local",
                "auto": True
            },
            {
                "name": "Videos",
                "keywords": ["video", "movie", "clip"],
                "paths": ["special://profile/Videos"],
                "protocol": "local",
                "auto": True
            }
        ]
        return self.get_setting('delivery_rules', default_rules)


    # Discrete naming
    @property
    def discrete_folder_template(self):
        opts = ['_', '__', 'custom']
        idx = self.get_setting('discrete_folder_template', 0)
        try:
            t = opts[int(idx)]
        except Exception:
            t = '_'
        if t == 'custom':
            return self.get_setting('discrete_folder_custom', '_') or '_'
        return t

    @property
    def discrete_bucket_template(self):
        opts = ['_', '__', 'custom']
        idx = self.get_setting('discrete_bucket_template', 0)
        try:
            t = opts[int(idx)]
        except Exception:
            t = '_'
        if t == 'custom':
            return self.get_setting('discrete_bucket_custom', '_') or '_'
        return t

# Global config instance
config = FluidConfig()