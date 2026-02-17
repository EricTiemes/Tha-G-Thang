import xbmc

class FluidLogger:
    """Unified logging with level control"""
    
    LEVELS = {
        'DEBUG': 0,
        'INFO': 1,
        'WARNING': 2,
        'ERROR': 3
    }
    
    def __init__(self, addon_id='plugin.video.fluid'):
        self.addon_id = addon_id
        self.level = self.LEVELS['INFO']
        self.debug_enabled = False
        
    def set_debug(self, enabled):
        self.debug_enabled = enabled
        self.level = self.LEVELS['DEBUG'] if enabled else self.LEVELS['INFO']
    
    def _log(self, message, level='INFO'):
        if self.LEVELS.get(level, 99) >= self.level:
            prefix = f"FLUID [{level}]: "
            kodi_level = {
                'DEBUG':   xbmc.LOGDEBUG,
                'INFO':    xbmc.LOGINFO,
                'WARNING': xbmc.LOGWARNING,
                'ERROR':   xbmc.LOGERROR,
            }.get(level, xbmc.LOGINFO)
            xbmc.log(prefix + str(message), level=kodi_level)
    
    def debug(self, msg):
        if self.debug_enabled:
            self._log(msg, 'DEBUG')
    
    def info(self, msg):
        self._log(msg, 'INFO')
    
    def warning(self, msg):
        self._log(msg, 'WARNING')
    
    def error(self, msg):
        self._log(msg, 'ERROR')

# Global logger instance
logger = FluidLogger()