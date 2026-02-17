import os
import json
import xbmc
import xbmcvfs

class Config:
    """Central configuration and environment abstraction"""
    
    # Default values for all settings
    DEFAULTS = {
        # General
        'general.auto_save': True,
        'general.max_log_age_days': 30,
        'general.show_wizard_tips': True,
        'general.power_user_mode': False,
        # Formats
        'format.default_json': True,
        'format.default_ai_handoff': True,
        'format.default_compact': False,
        'format.default_detailed': False,
        'format.auto_open': False,
        # Modules
        'module.enable_ui': True,
        'module.enable_db': True,
        'module.enable_network': True,
        'module.enable_runtime': True,
        'module.enable_fs': True,
        'module.enable_inject': False,
        # Research
        'research.auto_select_modules': True,
        'research.confirm_inject': True,
        # Advanced
        'advanced.debug_mode': False,
        'advanced.max_events_per_session': 10000,
        'advanced.buffer_size': 100
    }
    
    def __init__(self, addon):
        self.addon = addon
        self._init_paths()
        self._init_settings()
        
    def _init_paths(self):
        """Initialize all paths"""
        self.addon_id = self.addon.getAddonInfo('id')
        self.addon_path = xbmcvfs.translatePath(self.addon.getAddonInfo('path'))
        self.profile_path = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        
        # Subdirectories
        self.logs_path = os.path.join(self.profile_path, 'logs')
        self.cache_path = os.path.join(self.profile_path, 'cache')
        self.exports_path = os.path.join(self.profile_path, 'exports')
        self.data_path = os.path.join(self.profile_path, 'data')
        
        # Create directories
        for path in [self.profile_path, self.logs_path, self.cache_path, 
                     self.exports_path, self.data_path]:
            if not xbmcvfs.exists(path):
                xbmcvfs.mkdirs(path)
    
    def _init_settings(self):
        """Cache frequently used settings with safe fallbacks"""
        self.auto_save = self.get_bool('general.auto_save')
        self.debug_mode = self.get_bool('advanced.debug_mode')
        self.power_user = self.get_bool('general.power_user_mode')
        self.show_tips = self.get_bool('general.show_wizard_tips')
        
    def log(self, msg, level=xbmc.LOGINFO):
        """Log with addon prefix"""
        if self.debug_mode or level != xbmc.LOGDEBUG:
            xbmc.log(f"[FluidSnoop] {msg}", level)
    
    def get_setting(self, key):
        """Get string setting with fallback"""
        try:
            return self.addon.getSetting(key)
        except Exception:
            return self.DEFAULTS.get(key, '')
    
    def get_bool(self, key):
        """Get boolean setting with fallback"""
        try:
            return self.addon.getSettingBool(key)
        except Exception:
            return self.DEFAULTS.get(key, False)
    
    def get_int(self, key):
        """Get integer setting with fallback"""
        try:
            return self.addon.getSettingInt(key)
        except Exception:
            return self.DEFAULTS.get(key, 0)
    
    def set_setting(self, key, value):
        """Set setting value"""
        try:
            if isinstance(value, bool):
                self.addon.setSettingBool(key, value)
            elif isinstance(value, int):
                self.addon.setSettingInt(key, value)
            else:
                self.addon.setSetting(key, str(value))
        except Exception:
            pass
    
    def get_localized(self, string_id):
        """Get localized string"""
        try:
            return self.addon.getLocalizedString(string_id)
        except Exception:
            return str(string_id)
    
    def save_json(self, data, filename, subdir='exports'):
        """Save data as JSON"""
        path = os.path.join(getattr(self, f'{subdir}_path'), filename)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            return path
        except Exception as e:
            self.log(f"Save error: {e}", xbmc.LOGERROR)
            return None
    
    def load_json(self, filename, subdir='exports'):
        """Load JSON data"""
        path = os.path.join(getattr(self, f'{subdir}_path'), filename)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.log(f"Load error: {e}", xbmc.LOGERROR)
            return None
    
    def get_enabled_modules(self):
        """Get list of enabled modules from settings"""
        modules = []
        if self.get_bool('module.enable_ui'):
            modules.append('ui')
        if self.get_bool('module.enable_db'):
            modules.append('db')
        if self.get_bool('module.enable_network'):
            modules.append('network')
        if self.get_bool('module.enable_runtime'):
            modules.append('runtime')
        if self.get_bool('module.enable_fs'):
            modules.append('fs')
        if self.get_bool('module.enable_inject'):
            modules.append('inject')
        return modules
    
    def get_default_formats(self):
        """Get default output formats"""
        formats = []
        if self.get_bool('format.default_json'):
            formats.append('json')
        if self.get_bool('format.default_ai_handoff'):
            formats.append('ai_handoff')
        if self.get_bool('format.default_compact'):
            formats.append('compact')
        if self.get_bool('format.default_detailed'):
            formats.append('detailed')
        return formats