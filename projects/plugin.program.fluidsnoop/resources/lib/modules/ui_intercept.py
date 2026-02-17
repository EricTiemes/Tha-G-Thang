''"""
UI Intercept Module
Captures xbmcgui.Dialog calls, notifications, and user interactions
"""

import xbmcgui
import traceback
from datetime import datetime

class UIIntercept:
    """Intercepts and logs all UI interactions"""
    
    def __init__(self, config):
        self.config = config
        self.active = False
        self.original_dialog = None
        self.original_progress = None
        self.session_id = None
        self.buffer = []
        self.buffer_size = config.get_int('advanced.buffer_size')
        
    def start(self, session_id=None, target_filter=None):
        """Start UI monitoring"""
        if self.active:
            return
        
        self.session_id = session_id
        self.target_filter = target_filter
        self.buffer = []
        
        # Store originals
        self.original_dialog = xbmcgui.Dialog
        self.original_progress = xbmcgui.DialogProgress
        
        # Replace with wrapped versions
        xbmcgui.Dialog = self._create_wrapped_dialog()
        xbmcgui.DialogProgress = self._create_wrapped_progress()
        
        self.active = True
        self.config.log("UI intercept activated")
    
    def stop(self):
        """Stop UI monitoring and flush buffer"""
        if not self.active:
            return
        
        # Restore originals
        xbmcgui.Dialog = self.original_dialog
        xbmcgui.DialogProgress = self.original_progress
        
        self.active = False
        self._flush_buffer()
        self.config.log("UI intercept deactivated")
    
    def _create_wrapped_dialog(self):
        """Create wrapped Dialog class"""
        intercept = self
        original = self.original_dialog
        
        class WrappedDialog(original):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._intercept = intercept
            
            def ok(self, heading, message):
                self._intercept._log_call('ok', {
                    'heading': str(heading),
                    'message': str(message)[:500]
                })
                return super().ok(heading, message)
            
            def yesno(self, heading, message, nolabel='', yeslabel=''):
                self._intercept._log_call('yesno', {
                    'heading': str(heading),
                    'message': str(message)[:500],
                    'nolabel': str(nolabel),
                    'yeslabel': str(yeslabel)
                })
                return super().yesno(heading, message, nolabel, yeslabel)
            
            def notification(self, heading, message, icon=None, time=5000, sound=True):
                self._intercept._log_call('notification', {
                    'heading': str(heading),
                    'message': str(message)[:500],
                    'icon': str(icon) if icon else None,
                    'time': time,
                    'sound': sound
                })
                return super().notification(heading, message, icon, time, sound)
            
            def textviewer(self, heading, text):
                self._intercept._log_call('textviewer', {
                    'heading': str(heading),
                    'text': str(text)[:1000]
                })
                return super().textviewer(heading, text)
            
            def browse(self, type, heading, shares='', mask='', useThumbs=False,
                      treatAsFolder=False, defaultt='', enableMultiple=False):
                result = super().browse(type, heading, shares, mask, useThumbs,
                                       treatAsFolder, defaultt, enableMultiple)
                self._intercept._log_call('browse', {
                    'type': type,
                    'heading': str(heading),
                    'shares': shares,
                    'result': str(result)
                })
                return result
            
            def input(self, heading, default='', type=xbmcgui.INPUT_ALPHANUM, 
                     option=0, autoclose=0):
                result = super().input(heading, default, type, option, autoclose)
                self._intercept._log_call('input', {
                    'heading': str(heading),
                    'default': str(default),
                    'type': type,
                    'result': str(result)[:100] if result else None
                })
                return result
            
            def select(self, heading, list, autoclose=0, preselect=-1, useDetails=False):
                result = super().select(heading, list, autoclose, preselect, useDetails)
                self._intercept._log_call('select', {
                    'heading': str(heading),
                    'options': [str(x)[:100] for x in list[:10]],
                    'count': len(list),
                    'result': result
                })
                return result
            
            def multiselect(self, heading, options, autoclose=0, preselect=None, useDetails=False):
                result = super().multiselect(heading, options, autoclose, preselect, useDetails)
                self._intercept._log_call('multiselect', {
                    'heading': str(heading),
                    'options': [str(x)[:100] for x in options[:10]],
                    'count': len(options),
                    'result': result
                })
                return result
        
        return WrappedDialog
    
    def _create_wrapped_progress(self):
        """Create wrapped DialogProgress class"""
        intercept = self
        original = self.original_progress
        
        class WrappedProgress(original):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._intercept = intercept
                self._progress_id = datetime.now().isoformat()
            
            def create(self, heading, message=''):
                self._intercept._log_call('progress_create', {
                    'progress_id': self._progress_id,
                    'heading': str(heading),
                    'message': str(message)[:200]
                })
                return super().create(heading, message)
            
            def update(self, percent, message=''):
                # Throttle updates to avoid flooding
                if percent % 10 == 0 or percent in [0, 100]:
                    self._intercept._log_call('progress_update', {
                        'progress_id': self._progress_id,
                        'percent': percent,
                        'message': str(message)[:200]
                    })
                return super().update(percent, message)
            
            def close(self):
                self._intercept._log_call('progress_close', {
                    'progress_id': self._progress_id
                })
                return super().close()
            
            def iscanceled(self):
                result = super().iscanceled()
                if result:
                    self._intercept._log_call('progress_cancel', {
                        'progress_id': self._progress_id
                    })
                return result
        
        return WrappedProgress
    
    def _log_call(self, method, params):
        """Log UI call to buffer"""
        entry = {
            'time': datetime.now().isoformat(),
            'type': 'ui_dialog',
            'method': method,
            'params': params,
            'caller': self._get_caller()
        }
        
        # Check target filter
        if self.target_filter:
            caller_str = str(entry['caller'])
            if self.target_filter not in caller_str:
                return
        
        self.buffer.append(entry)
        
        # Flush if buffer full
        if len(self.buffer) >= self.buffer_size:
            self._flush_buffer()
    
    def _get_caller(self):
        """Get calling addon from stack trace"""
        stack = traceback.extract_stack()
        for frame in reversed(stack):
            filename = str(frame.filename)
            # Look for addon patterns
            if any(x in filename for x in ['plugin.', 'script.', 'service.']):
                return {
                    'file': filename,
                    'line': frame.lineno,
                    'function': frame.name
                }
        return {'file': 'unknown', 'line': 0, 'function': 'unknown'}
    
    def _flush_buffer(self):
        """Write buffered events to database"""
        if not self.buffer:
            return
        
        # Import here to avoid circular dependency
        from persistence.database import Database
        db = Database(self.config)
        
        for entry in self.buffer:
            db.add_event(
                session_id=self.session_id,
                module='ui',
                event_type=entry['method'],
                data=entry
            )
        
        self.buffer = []
    
    def get_stats(self):
        """Get module statistics"""
        return {
            'active': self.active,
            'buffered': len(self.buffer),
            'session': self.session_id
        }