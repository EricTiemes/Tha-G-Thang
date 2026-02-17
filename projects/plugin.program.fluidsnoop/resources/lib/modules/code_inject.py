import os
from datetime import datetime

class CodeInject:
    """Generates code injection snippets"""
    
    def __init__(self, config):
        self.config = config
        
    def generate(self, addon_id, injection_type='logger', target_file='default.py'):
        """Generate injection snippet"""
        if injection_type == 'logger':
            return self._generate_logger(addon_id, target_file)
        elif injection_type == 'tracer':
            return self._generate_tracer(addon_id, target_file)
        elif injection_type == 'ui_tracker':
            return self._generate_ui_tracker(addon_id, target_file)
        elif injection_type == 'db_tracker':
            return self._generate_db_tracker(addon_id, target_file)
        else:
            return self._generate_custom(addon_id, injection_type)
    
    def _generate_logger(self, addon_id, target_file):
        """Generate basic logger snippet"""
        code = f"""# FluidSnoop Logger Injection for {addon_id}
# Insert this at the top of {target_file}

import json
import xbmc
import xbmcvfs
from datetime import datetime

class SnoopLogger:
    def __init__(self, addon_id="{addon_id}"):
        self.addon_id = addon_id
        self.log_file = xbmcvfs.translatePath(
            f"special://profile/addon_data/plugin.program.fluidsnoop/logs/{{addon_id}}_snoop.json"
        )
        self.entries = []
        self._init_log()
    
    def _init_log(self):
        # Load existing log if present
        if xbmcvfs.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    self.entries = json.load(f)
            except Exception:
                self.entries = []
    
    def log(self, event_type, data):
        entry = {{
            'time': datetime.now().isoformat(),
            'addon': self.addon_id,
            'type': event_type,
            'data': data
        }}
        self.entries.append(entry)
        xbmc.log(f"[SNOOP] {{event_type}}: {{data}}", xbmc.LOGINFO)
        # Auto-save every 10 entries
        if len(self.entries) % 10 == 0:
            self.save()
    
    def save(self):
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.entries, f, indent=2, default=str)
        except Exception as e:
            xbmc.log(f"[SNOOP] Save error: {{e}}", xbmc.LOGERROR)

# Initialize logger
snoop = SnoopLogger()

# Usage examples:
# snoop.log('favorite_add', {{'name': item_name, 'url': item_url}})
# snoop.log('menu_click', {{'item': item_label, 'path': item_path}})
# snoop.log('api_call', {{'url': api_url, 'params': params}})

# IMPORTANT: Call snoop.save() before addon exits or on error
"""
        return self._save_snippet(addon_id, 'logger', code)
    
    def _generate_tracer(self, addon_id, target_file):
        """Generate function tracer snippet"""
        code = f"""# FluidSnoop Function Tracer for {addon_id}
# Insert this at the top of {target_file}

import functools
import xbmc
from datetime import datetime
import json
import xbmcvfs

# Tracer log storage
_TRACER_LOG_FILE = xbmcvfs.translatePath(
    "special://profile/addon_data/plugin.program.fluidsnoop/logs/{addon_id}_tracer.json"
)
_tracer_entries = []

def _save_tracer_log():
    try:
        with open(_TRACER_LOG_FILE, 'w') as f:
            json.dump(_tracer_entries, f, indent=2, default=str)
    except Exception as e:
        xbmc.log(f"[TRACER] Save error: {{e}}", xbmc.LOGERROR)

def trace_calls(func):
    """Decorator to trace function calls"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        call_info = {{
            'time': datetime.now().isoformat(),
            'addon': '{addon_id}',
            'function': func.__name__,
            'module': func.__module__ if hasattr(func, '__module__') else 'unknown',
            'args': str(args)[:200],
            'kwargs': str(kwargs)[:200]
        }}
        
        xbmc.log(f"[TRACER] Calling {{func.__name__}}", xbmc.LOGDEBUG)
        
        try:
            result = func(*args, **kwargs)
            call_info['status'] = 'success'
            call_info['result'] = str(result)[:200]
            call_info['duration_ms'] = 0  # Could add timing
            return result
        except Exception as e:
            call_info['status'] = 'error'
            call_info['error'] = str(e)
            raise
        finally:
            _tracer_entries.append(call_info)
            if len(_tracer_entries) % 5 == 0:
                _save_tracer_log()
            xbmc.log(f"[TRACER] {{call_info['status']}}: {{func.__name__}}", xbmc.LOGDEBUG)
    
    return wrapper

# Usage:
# @trace_calls
# def add_to_favorites(item):
#     # your code here

# IMPORTANT: Call _save_tracer_log() before addon exits
"""
        return self._save_snippet(addon_id, 'tracer', code)
    
    def _generate_ui_tracker(self, addon_id, target_file):
        """Generate UI tracking snippet"""
        code = f"""# FluidSnoop UI Tracker for {addon_id}
# Insert this after importing xbmcgui

import xbmcgui
import json
import xbmcvfs
from datetime import datetime

_UI_LOG_FILE = xbmcvfs.translatePath(
    "special://profile/addon_data/plugin.program.fluidsnoop/logs/{addon_id}_ui.json"
)
_ui_entries = []

def _save_ui_log():
    try:
        with open(_UI_LOG_FILE, 'w') as f:
            json.dump(_ui_entries, f, indent=2, default=str)
    except Exception:
        pass

# Store original Dialog
_OriginalDialog = xbmcgui.Dialog

class _TrackedDialog(_OriginalDialog):
    def notification(self, heading, message, icon=None, time=5000, sound=True):
        _ui_entries.append({{
            'time': datetime.now().isoformat(),
            'type': 'notification',
            'heading': str(heading),
            'message': str(message)[:200]
        }})
        _save_ui_log()
        return super().notification(heading, message, icon, time, sound)
    
    def ok(self, heading, message):
        _ui_entries.append({{
            'time': datetime.now().isoformat(),
            'type': 'ok_dialog',
            'heading': str(heading),
            'message': str(message)[:500]
        }})
        _save_ui_log()
        return super().ok(heading, message)

# Replace Dialog class
xbmcgui.Dialog = _TrackedDialog

# IMPORTANT: Logs save automatically after each UI call
"""
        return self._save_snippet(addon_id, 'ui_tracker', code)
    
    def _generate_db_tracker(self, addon_id, target_file):
        """Generate DB tracking snippet"""
        code = f"""# FluidSnoop DB Tracker for {addon_id}
# Insert this after importing sqlite3

import sqlite3
import json
import xbmcvfs
from datetime import datetime

_DB_LOG_FILE = xbmcvfs.translatePath(
    "special://profile/addon_data/plugin.program.fluidsnoop/logs/{addon_id}_db.json"
)
_db_entries = []

def _save_db_log():
    try:
        with open(_DB_LOG_FILE, 'w') as f:
            json.dump(_db_entries, f, indent=2, default=str)
    except Exception:
        pass

# Store original connect
_original_connect = sqlite3.connect

def _tracked_connect(database, *args, **kwargs):
    conn = _original_connect(database, *args, **kwargs)
    original_execute = conn.execute
    
    def tracked_execute(sql, parameters=()):
        _db_entries.append({{
            'time': datetime.now().isoformat(),
            'database': str(database),
            'sql': str(sql)[:500],
            'params': str(parameters)[:200]
        }})
        if len(_db_entries) % 5 == 0:
            _save_db_log()
        return original_execute(sql, parameters)
    
    conn.execute = tracked_execute
    return conn

# Replace connect
sqlite3.connect = _tracked_connect

# IMPORTANT: Call _save_db_log() before closing connections
"""
        return self._save_snippet(addon_id, 'db_tracker', code)
    
    def _save_snippet(self, addon_id, snippet_type, code):
        """Save snippet to file"""
        filename = f"{addon_id}_{snippet_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        path = os.path.join(self.config.exports_path, filename)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        instructions = [
            f"1. Open {addon_id}/default.py (or main file)",
            f"2. Copy the code above to the TOP of the file",
            f"3. For functions you want to trace, add @trace_calls decorator",
            f"4. Add snoop.log() calls at key points",
            f"5. Ensure snoop.save() or _save_*_log() is called before exit",
            f"6. Run the addon normally",
            f"7. Check {self.config.logs_path} for output"
        ]
        
        return {
            'type': snippet_type,
            'code': code,
            'path': path,
            'instructions': instructions,
            'target_addon': addon_id
        }
    
    def _generate_custom(self, addon_id, custom_type):
        """Handle custom injection types"""
        return {
            'type': 'custom',
            'message': f'Custom injection type "{custom_type}" not implemented',
            'available_types': ['logger', 'tracer', 'ui_tracker', 'db_tracker']
        }