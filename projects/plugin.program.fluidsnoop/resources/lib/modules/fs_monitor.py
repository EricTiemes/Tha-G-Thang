import os
import shutil
import xbmcvfs
from datetime import datetime

class FSMonitor:
    """Monitors filesystem operations"""
    
    def __init__(self, config):
        self.config = config
        self.active = False
        self.original_xbmcvfs_copy = None
        self.original_xbmcvfs_delete = None
        self.original_xbmcvfs_exists = None
        self.original_shutil_copy = None
        self.original_os_remove = None
        self.session_id = None
        self.target_filter = None
        self.buffer = []
        self.buffer_size = config.get_int('advanced.buffer_size')
        
    def start(self, session_id=None, target_filter=None):
        """Start filesystem monitoring"""
        if self.active:
            return
        
        self.session_id = session_id
        self.target_filter = target_filter
        self.buffer = []
        
        # Hook xbmcvfs
        self.original_xbmcvfs_copy = xbmcvfs.copy
        self.original_xbmcvfs_delete = xbmcvfs.delete
        self.original_xbmcvfs_exists = xbmcvfs.exists
        
        xbmcvfs.copy = self._wrapped_xbmcvfs_copy
        xbmcvfs.delete = self._wrapped_xbmcvfs_delete
        xbmcvfs.exists = self._wrapped_xbmcvfs_exists
        
        # Hook shutil
        self.original_shutil_copy = shutil.copy
        shutil.copy = self._wrapped_shutil_copy
        
        # Hook os.remove
        self.original_os_remove = os.remove
        os.remove = self._wrapped_os_remove
        
        self.active = True
        self.config.log("Filesystem monitor activated")
    
    def stop(self):
        """Stop monitoring and flush buffer"""
        if not self.active:
            return
        
        xbmcvfs.copy = self.original_xbmcvfs_copy
        xbmcvfs.delete = self.original_xbmcvfs_delete
        xbmcvfs.exists = self.original_xbmcvfs_exists
        shutil.copy = self.original_shutil_copy
        os.remove = self.original_os_remove
        
        self.active = False
        self._flush_buffer()
        self.config.log("Filesystem monitor deactivated")
    
    def _should_log(self, path):
        """Check if path should be logged"""
        if not self.target_filter:
            return True
        return self.target_filter in str(path)
    
    def _wrapped_xbmcvfs_copy(self, src, dst):
        """Wrap xbmcvfs.copy"""
        if self._should_log(src) or self._should_log(dst):
            self._log_operation('xbmcvfs.copy', {
                'source': str(src),
                'destination': str(dst)
            })
        return self.original_xbmcvfs_copy(src, dst)
    
    def _wrapped_xbmcvfs_delete(self, path):
        """Wrap xbmcvfs.delete"""
        if self._should_log(path):
            self._log_operation('xbmcvfs.delete', {
                'path': str(path)
            })
        return self.original_xbmcvfs_delete(path)
    
    def _wrapped_xbmcvfs_exists(self, path):
        """Wrap xbmcvfs.exists"""
        result = self.original_xbmcvfs_exists(path)
        if self._should_log(path):
            self._log_operation('xbmcvfs.exists', {
                'path': str(path),
                'result': bool(result)
            })
        return result
    
    def _wrapped_shutil_copy(self, src, dst, *args, **kwargs):
        """Wrap shutil.copy"""
        if self._should_log(src) or self._should_log(dst):
            self._log_operation('shutil.copy', {
                'source': str(src),
                'destination': str(dst)
            })
        return self.original_shutil_copy(src, dst, *args, **kwargs)
    
    def _wrapped_os_remove(self, path):
        """Wrap os.remove"""
        if self._should_log(path):
            self._log_operation('os.remove', {
                'path': str(path)
            })
        return self.original_os_remove(path)
    
    def _log_operation(self, operation, details):
        """Log filesystem operation"""
        entry = {
            'time': datetime.now().isoformat(),
            'type': 'filesystem',
            'operation': operation,
            'details': details
        }
        
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
                module='fs',
                event_type=entry['operation'],
                data=entry
            )
        
        self.buffer = []
    
    def get_stats(self):
        """Get module statistics"""
        operations = {}
        for entry in self.buffer:
            op = entry['operation']
            operations[op] = operations.get(op, 0) + 1
        
        return {
            'active': self.active,
            'buffered': len(self.buffer),
            'operations': operations
        }