import builtins
import functools
from datetime import datetime
import traceback

class RuntimeHook:
    """Hooks into module imports and function calls"""
    
    def __init__(self, config):
        self.config = config
        self.active = False
        self.original_import = None
        self.hooked_modules = {}
        self.session_id = None
        self.target_filter = None
        self.buffer = []
        self.buffer_size = config.get_int('advanced.buffer_size')
        self.call_depth = 0
        self.max_depth = 10  # Prevent infinite recursion
        
    def start(self, session_id=None, target_filter=None):
        """Start runtime hooking"""
        if self.active:
            return
        
        self.session_id = session_id
        self.target_filter = target_filter
        self.buffer = []
        self.hooked_modules = {}
        
        # Hook __import__
        self.original_import = builtins.__import__
        builtins.__import__ = self._hook_import
        
        self.active = True
        self.config.log("Runtime hooks activated")
    
    def stop(self):
        """Stop hooking and flush buffer"""
        if not self.active:
            return
        
        builtins.__import__ = self.original_import
        
        self.active = False
        self._flush_buffer()
        self.config.log("Runtime hooks deactivated")
    
    def _hook_import(self, name, *args, **kwargs):
        """Wrap import statements"""
        module = self.original_import(name, *args, **kwargs)
        
        # Check if we should hook this module
        if self._should_hook(name):
            if name not in self.hooked_modules:
                self._wrap_module(name, module)
                self.hooked_modules[name] = True
        
        return module
    
    def _should_hook(self, name):
        """Determine if module should be hooked"""
        # Target filter takes precedence
        if self.target_filter:
            return self.target_filter in name
        
        # Hook addon patterns
        patterns = ['plugin.', 'script.', 'service.']
        return any(p in name for p in patterns)
    
    def _wrap_module(self, name, module):
        """Wrap module functions"""
        try:
            for attr_name in dir(module):
                if attr_name.startswith('_'):
                    continue
                
                try:
                    obj = getattr(module, attr_name)
                    if callable(obj) and not isinstance(obj, type):
                        wrapped = self._wrap_function(name, attr_name, obj)
                        setattr(module, attr_name, wrapped)
                except Exception:
                    pass
        except Exception:
            pass
    
    def _wrap_function(self, module_name, func_name, func):
        """Create wrapped function"""
        hook = self
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Prevent recursion
            if hook.call_depth >= hook.max_depth:
                return func(*args, **kwargs)
            
            hook.call_depth += 1
            start = datetime.now()
            
            entry = {
                'time': start.isoformat(),
                'type': 'runtime_call',
                'module': module_name,
                'function': func_name,
                'args': hook._safe_repr(args),
                'kwargs': hook._safe_repr(kwargs),
                'caller': hook._get_caller()
            }
            
            try:
                result = func(*args, **kwargs)
                entry['status'] = 'success'
                entry['result'] = hook._safe_repr(result)
                entry['duration_ms'] = int((datetime.now() - start).total_seconds() * 1000)
                
                hook._log_entry(entry)
                hook.call_depth -= 1
                return result
                
            except Exception as e:
                entry['status'] = 'error'
                entry['error'] = str(e)
                entry['duration_ms'] = int((datetime.now() - start).total_seconds() * 1000)
                hook._log_entry(entry)
                hook.call_depth -= 1
                raise
        
        return wrapper
    
    def _safe_repr(self, obj, max_len=200):
        """Safely represent object as string"""
        try:
            s = repr(obj)
            if len(s) > max_len:
                s = s[:max_len] + '...'
            return s
        except Exception:
            return '<unrepr>'
    
    def _get_caller(self):
        """Get calling context"""
        try:
            stack = traceback.extract_stack()
            # Find first frame outside this module
            for frame in reversed(stack[:-2]):  # Exclude current and wrapper
                filename = str(frame.filename)
                if 'fluidsnoop' not in filename.lower():
                    return {
                        'file': filename,
                        'line': frame.lineno,
                        'function': frame.name
                    }
        except Exception:
            pass
        return {'file': 'unknown', 'line': 0, 'function': 'unknown'}
    
    def _log_entry(self, entry):
        """Add entry to buffer"""
        self.buffer.append(entry)
        
        if len(self.buffer) >= self.buffer_size:
            self._flush_buffer()
    
    def _flush_buffer(self):
        """Write buffered events to database"""
        if not self.buffer:
            return
        
        from persistence.database import Database
        db = Database(self.config)
        
        for entry in self.buffer:
            db.add_event(
                session_id=self.session_id,
                module='runtime',
                event_type=entry['function'],
                data=entry
            )
        
        self.buffer = []
    
    def get_call_tree(self):
        """Get hierarchical call structure"""
        tree = {}
        for entry in self.buffer:
            module = entry.get('module', 'unknown')
            func = entry.get('function', 'unknown')
            
            if module not in tree:
                tree[module] = {}
            if func not in tree[module]:
                tree[module][func] = {'calls': 0, 'errors': 0}
            
            tree[module][func]['calls'] += 1
            if entry.get('status') == 'error':
                tree[module][func]['errors'] += 1
        
        return tree
    
    def get_stats(self):
        """Get module statistics"""
        total_calls = len(self.buffer)
        errors = sum(1 for e in self.buffer if e.get('status') == 'error')
        modules = len(set(e.get('module', '') for e in self.buffer))
        
        return {
            'active': self.active,
            'buffered': total_calls,
            'modules_hooked': len(self.hooked_modules),
            'unique_modules': modules,
            'errors': errors
        }