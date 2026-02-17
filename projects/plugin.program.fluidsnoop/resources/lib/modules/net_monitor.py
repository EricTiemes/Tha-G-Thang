import urllib.request
import urllib.error
from datetime import datetime

class NetMonitor:
    """Monitors network operations"""
    
    def __init__(self, config):
        self.config = config
        self.active = False
        self.original_urlopen = None
        self.session_id = None
        self.target_filter = None
        self.buffer = []
        self.buffer_size = config.get_int('advanced.buffer_size')
        
    def start(self, session_id=None, target_filter=None):
        """Start network monitoring"""
        if self.active:
            return
        
        self.session_id = session_id
        self.target_filter = target_filter
        self.buffer = []
        
        # Hook urllib
        self.original_urlopen = urllib.request.urlopen
        urllib.request.urlopen = self._wrapped_urlopen
        
        # Try to hook requests library if available
        self._hook_requests()
        
        self.active = True
        self.config.log("Network monitor activated")
    
    def stop(self):
        """Stop monitoring and flush buffer"""
        if not self.active:
            return
        
        urllib.request.urlopen = self.original_urlopen
        self._unhook_requests()
        
        self.active = False
        self._flush_buffer()
        self.config.log("Network monitor deactivated")
    
    def _wrapped_urlopen(self, url, data=None, timeout=None, *args, **kwargs):
        """Wrap urlopen calls"""
        start = datetime.now()
        url_str = str(url)
        
        # Check target filter
        if self.target_filter and self.target_filter not in url_str:
            return self.original_urlopen(url, data, timeout, *args, **kwargs)
        
        try:
            response = self.original_urlopen(url, data, timeout, *args, **kwargs)
            duration = int((datetime.now() - start).total_seconds() * 1000)
            
            self._log_request(
                url=url_str,
                method='POST' if data else 'GET',
                data_size=len(data) if data else 0,
                status=response.getcode(),
                headers=dict(response.headers) if hasattr(response, 'headers') else {},
                duration=duration,
                error=None
            )
            
            return response
            
        except Exception as e:
            duration = int((datetime.now() - start).total_seconds() * 1000)
            self._log_request(
                url=url_str,
                method='POST' if data else 'GET',
                data_size=len(data) if data else 0,
                status=None,
                headers={},
                duration=duration,
                error=str(e)
            )
            raise
    
    def _hook_requests(self):
        """Hook requests library if available"""
        try:
            import requests
            self._original_requests_get = requests.get
            self._original_requests_post = requests.post
            
            def wrapped_get(url, **kwargs):
                return self._wrapped_requests('GET', url, **kwargs)
            
            def wrapped_post(url, **kwargs):
                return self._wrapped_requests('POST', url, **kwargs)
            
            requests.get = wrapped_get
            requests.post = wrapped_post
            self._requests_hooked = True
            
        except ImportError:
            self._requests_hooked = False
    
    def _unhook_requests(self):
        """Unhook requests library"""
        if hasattr(self, '_requests_hooked') and self._requests_hooked:
            try:
                import requests
                requests.get = self._original_requests_get
                requests.post = self._original_requests_post
            except Exception:
                pass
    
    def _wrapped_requests(self, method, url, **kwargs):
        """Wrap requests library calls"""
        start = datetime.now()
        url_str = str(url)
        
        # Check target filter
        if self.target_filter and self.target_filter not in url_str:
            if method == 'GET':
                return self._original_requests_get(url, **kwargs)
            else:
                return self._original_requests_post(url, **kwargs)
        
        try:
            if method == 'GET':
                response = self._original_requests_get(url, **kwargs)
            else:
                response = self._original_requests_post(url, **kwargs)
            
            duration = int((datetime.now() - start).total_seconds() * 1000)
            
            self._log_request(
                url=url_str,
                method=method,
                data_size=len(kwargs.get('data', '')) if kwargs.get('data') else 0,
                status=response.status_code,
                headers=dict(response.headers) if hasattr(response, 'headers') else {},
                duration=duration,
                error=None,
                source='requests'
            )
            
            return response
            
        except Exception as e:
            duration = int((datetime.now() - start).total_seconds() * 1000)
            self._log_request(
                url=url_str,
                method=method,
                data_size=0,
                status=None,
                headers={},
                duration=duration,
                error=str(e),
                source='requests'
            )
            raise
    
    def _log_request(self, url, method, data_size, status, headers, duration, error, source='urllib'):
        """Log network request"""
        entry = {
            'time': datetime.now().isoformat(),
            'type': 'network',
            'source': source,
            'url': url[:500],
            'method': method,
            'data_size': data_size,
            'status': status,
            'headers': {k: v for k, v in headers.items() if k.lower() in ['content-type', 'content-length', 'user-agent']},
            'duration_ms': duration,
            'error': error
        }
        
        # Extract domain and path pattern
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            entry['domain'] = parsed.netloc
            entry['path'] = parsed.path[:100]
        except Exception:
            pass
        
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
                module='network',
                event_type=entry['method'],
                data=entry
            )
        
        self.buffer = []
    
    def extract_patterns(self):
        """Extract URL patterns from captured requests"""
        domains = {}
        for entry in self.buffer:
            domain = entry.get('domain', 'unknown')
            if domain not in domains:
                domains[domain] = {'count': 0, 'paths': []}
            domains[domain]['count'] += 1
            if entry.get('path'):
                domains[domain]['paths'].append(entry['path'])
        
        return domains
    
    def get_stats(self):
        """Get module statistics"""
        domains = set()
        methods = {}
        for entry in self.buffer:
            if entry.get('domain'):
                domains.add(entry['domain'])
            method = entry.get('method', 'UNKNOWN')
            methods[method] = methods.get(method, 0) + 1
        
        return {
            'active': self.active,
            'buffered': len(self.buffer),
            'unique_domains': len(domains),
            'methods': methods
        }