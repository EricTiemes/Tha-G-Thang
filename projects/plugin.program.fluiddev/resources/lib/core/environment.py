"""
FluidDev - Environment Abstraction Layer
Abstract base classes for Kodi vs Dev environments.
"""
from abc import ABC, abstractmethod
import os


class Environment(ABC):
    """Abstract base for runtime environment."""
    
    @property
    @abstractmethod
    def name(self):
        """Environment name."""
        pass
    
    @abstractmethod
    def log(self, message, level=1):
        """Log message."""
        pass
    
    @abstractmethod
    def translate_path(self, path):
        """Convert special:// paths."""
        pass
    
    @abstractmethod
    def vfs_exists(self, path):
        """Check if path exists."""
        pass
    
    @abstractmethod
    def vfs_listdir(self, path):
        """List directory contents."""
        pass
    
    @abstractmethod
    def notification(self, title, message, icon="INFO", time=3000):
        """Show notification."""
        pass
    
    @abstractmethod
    def dialog_ok(self, heading, message):
        """Show OK dialog."""
        pass
    
    @abstractmethod
    def dialog_select(self, heading, options):
        """Show select dialog, return index."""
        pass
    
    @abstractmethod
    def dialog_input(self, heading, default=""):
        """Show input dialog."""
        pass
    
    @abstractmethod
    def get_addon_info(self, info_id):
        """Get addon metadata."""
        pass
    
    @abstractmethod
    def get_setting(self, setting_id, default=""):
        """Get setting value."""
        pass
    
    @abstractmethod
    def set_setting(self, setting_id, value):
        """Set setting value."""
        pass
    
    @abstractmethod
    def open_settings(self):
        """Open settings dialog."""
        pass


class KodiEnvironment(Environment):
    """Real Kodi environment using xbmc modules."""
    
    def __init__(self):
        import xbmc
        import xbmcaddon
        import xbmcvfs
        import xbmcgui
        
        self.xbmc = xbmc
        self.addon = xbmcaddon.Addon()
        self.vfs = xbmcvfs
        self.gui = xbmcgui
        
        self._addon_id = self.addon.getAddonInfo('id')
        self._addon_path = self.vfs.translatePath(self.addon.getAddonInfo('path'))
        self._profile_path = self.vfs.translatePath(self.addon.getAddonInfo('profile'))
    
    @property
    def name(self):
        return "kodi"
    
    def log(self, message, level=1):
        levels = {
            0: self.xbmc.LOGDEBUG,
            1: self.xbmc.LOGINFO,
            2: self.xbmc.LOGWARNING,
            3: self.xbmc.LOGERROR
        }
        self.xbmc.log(f"[{self._addon_id}] {message}", levels.get(level, self.xbmc.LOGINFO))
    
    def translate_path(self, path):
        return self.vfs.translatePath(path)
    
    def vfs_exists(self, path):
        return self.vfs.exists(path)
    
    def vfs_listdir(self, path):
        return self.vfs.listdir(path)
    
    def notification(self, title, message, icon="INFO", time=3000):
        icons = {
            "INFO": self.gui.NOTIFICATION_INFO,
            "WARNING": self.gui.NOTIFICATION_WARNING,
            "ERROR": self.gui.NOTIFICATION_ERROR
        }
        self.gui.Dialog().notification(title, message, icons.get(icon, icons["INFO"]), time)
    
    def dialog_ok(self, heading, message):
        self.gui.Dialog().ok(heading, message)
    
    def dialog_select(self, heading, options):
        return self.gui.Dialog().select(heading, options)
    
    def dialog_input(self, heading, default=""):
        return self.gui.Dialog().input(heading, default)
    
    def get_addon_info(self, info_id):
        return self.addon.getAddonInfo(info_id)
    
    def get_setting(self, setting_id, default=""):
        val = self.addon.getSetting(setting_id)
        return val if val else default
    
    def set_setting(self, setting_id, value):
        return self.addon.setSetting(setting_id, str(value))
    
    def open_settings(self):
        self.addon.openSettings()


class DevEnvironment(Environment):
    """Development environment with CLI fallbacks."""
    
    def __init__(self, addon_path=None):
        self._addon_id = "plugin.program.fluiddev"
        self._addon_path = addon_path or "/storage/emulated/0/Documents/EricTiemes/Tha-G-Thang/public/FluidDev/plugin.program.fluiddev"
        self._profile_path = "/storage/emulated/0/Download/FluidDevData"
        self._settings = self._load_settings()
        
        os.makedirs(self._profile_path, exist_ok=True)
    
    def _load_settings(self):
        """Load settings from JSON file."""
        settings_file = os.path.join(self._profile_path, "dev_settings.json")
        if os.path.exists(settings_file):
            import json
            with open(settings_file, 'r') as f:
                return json.load(f)
        return {
            "max_scan_files": "100",
            "deep_analysis": "true",
            "include_system": "false",
            "ast_depth": "medium",
            "addons_path": "special://home/addons",
            "output_path": "special://profile/addon_data/plugin.program.fluiddev",
            "acode_export_path": "/storage/emulated/0/Download/FluidDevExports",
            "auto_clean": "true",
            "clean_paths": "true",
            "generalize_vars": "true",
            "clean_comments": "true",
            "report_format": "markdown",
            "auto_save": "true",
            "auto_handoff": "true",
            "include_snippets": "true"
        }
    
    def _save_settings(self):
        """Save settings to JSON file."""
        import json
        settings_file = os.path.join(self._profile_path, "dev_settings.json")
        with open(settings_file, 'w') as f:
            json.dump(self._settings, f, indent=2)
    
    @property
    def name(self):
        return "dev"
    
    def log(self, message, level=1):
        prefix = ["DEBUG", "INFO", "WARNING", "ERROR"][min(level, 3)]
        print(f"[{prefix}] [{self._addon_id}] {message}")
    
    def translate_path(self, path):
        """Convert special:// paths for dev environment."""
        translations = {
            "special://home": "/storage/emulated/0/Android/data/org.xbmc.kodi/files/.kodi",
            "special://profile": "/storage/emulated/0/Android/data/org.xbmc.kodi/files/.kodi/userdata",
            "special://temp": "/storage/emulated/0/Download/FluidDevTemp"
        }
        for special, real in translations.items():
            if path.startswith(special):
                return path.replace(special, real)
        return path
    
    def vfs_exists(self, path):
        real_path = self.translate_path(path)
        return os.path.exists(real_path)
    
    def vfs_listdir(self, path):
        real_path = self.translate_path(path)
        try:
            items = os.listdir(real_path)
            dirs = [i for i in items if os.path.isdir(os.path.join(real_path, i))]
            files = [i for i in items if os.path.isfile(os.path.join(real_path, i))]
            return dirs, files
        except Exception:
            return [], []
    
    def notification(self, title, message, icon="INFO", time=3000):
        print(f"\n[NOTIFICATION] {title}: {message}")
    
    def dialog_ok(self, heading, message):
        print(f"\n[DIALOG] {heading}")
        print(message)
        input("Press Enter to continue...")
    
    def dialog_select(self, heading, options):
        print(f"\n{heading}")
        for i, opt in enumerate(options):
            print(f"  [{i}] {opt}")
        try:
            result = input("Select (number): ")
            return int(result) if result.isdigit() and int(result) < len(options) else -1
        except (KeyboardInterrupt, EOFError):
            return -1
    
    def dialog_input(self, heading, default=""):
        print(f"\n{heading}")
        if default:
            print(f"Default: {default}")
        result = input("> ")
        return result if result else default
    
    def get_addon_info(self, info_id):
        info = {
            "id": self._addon_id,
            "name": "FluidDev",
            "version": "1.1.0",
            "path": self._addon_path,
            "profile": self._profile_path,
            "author": "FluidDev Team"
        }
        return info.get(info_id, "")
    
    def get_setting(self, setting_id, default=""):
        return self._settings.get(setting_id, default)
    
    def set_setting(self, setting_id, value):
        self._settings[setting_id] = str(value)
        self._save_settings()
        return True
    
    def open_settings(self):
        print("\n[SETTINGS] Would open settings dialog in Kodi")
        print("Current settings:")
        for k, v in self._settings.items():
            print(f"  {k}: {v}")
