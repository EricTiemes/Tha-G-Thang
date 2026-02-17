"""
Pattern Extractor Module
Analyzes captured events to identify reusable patterns
"""

import re
from collections import defaultdict

class PatternExtract:
    """Extracts patterns from captured events"""
    
    def __init__(self, config):
        self.config = config
        
    def extract(self, session_id, db, pattern_type='all'):
        """Extract patterns from session events"""
        events = db.get_events(session_id)
        
        if pattern_type == 'favorites':
            return self._extract_favorites_pattern(events)
        elif pattern_type == 'download':
            return self._extract_download_pattern(events)
        elif pattern_type == 'menu':
            return self._extract_menu_pattern(events)
        elif pattern_type == 'api':
            return self._extract_api_pattern(events)
        elif pattern_type == 'auth':
            return self._extract_auth_pattern(events)
        else:
            return self._extract_all_patterns(events)
    
    def _extract_favorites_pattern(self, events):
        """Extract favorites implementation pattern"""
        pattern = {
            'type': 'favorites',
            'db_operations': [],
            'ui_feedback': [],
            'code_sequence': [],
            'count': 0
        }
        
        for event in events:
            data = event.get('data', {})
            
            # DB operations related to favorites
            if event['module'] == 'db':
                sql = data.get('sql', '').upper()
                if any(k in sql for k in ['FAVORITE', 'BOOKMARK', 'FAV']):
                    pattern['db_operations'].append({
                        'sql': data.get('sql'),
                        'params': data.get('params'),
                        'operation': data.get('operation'),
                        'tables': data.get('tables', [])
                    })
                    pattern['count'] += 1
            
            # UI feedback
            if event['module'] == 'ui':
                params = data.get('params', {})
                msg = str(params).lower()
                if any(k in msg for k in ['favorite', 'bookmark', 'added', 'removed']):
                    pattern['ui_feedback'].append({
                        'method': data.get('method'),
                        'heading': params.get('heading', ''),
                        'message': params.get('message', '')
                    })
        
        # Generate code template
        pattern['code_sequence'] = self._build_favorites_code(pattern)
        
        return pattern
    
    def _extract_download_pattern(self, events):
        """Extract download flow pattern"""
        pattern = {
            'type': 'download',
            'network_calls': [],
            'file_operations': [],
            'ui_progress': [],
            'sequence': [],
            'count': 0
        }
        
        for event in events:
            data = event.get('data', {})
            
            # Network calls
            if event['module'] == 'network':
                url = data.get('url', '')
                if any(ext in url.lower() for ext in ['.mp4', '.mkv', '.avi', '.zip', '.tar']):
                    pattern['network_calls'].append({
                        'url': url,
                        'method': data.get('method'),
                        'status': data.get('status'),
                        'duration_ms': data.get('duration_ms')
                    })
                    pattern['sequence'].append(('download', url[:100]))
                    pattern['count'] += 1
            
            # File operations
            if event['module'] == 'fs':
                op = data.get('operation', '')
                details = data.get('details', {})
                if any(x in op for x in ['copy', 'delete', 'remove']):
                    pattern['file_operations'].append({
                        'operation': op,
                        'source': details.get('source', details.get('path', '')),
                        'destination': details.get('destination', '')
                    })
                    pattern['sequence'].append(('file_op', op))
            
            # UI progress
            if event['module'] == 'ui':
                method = data.get('method', '')
                if 'progress' in method:
                    pattern['ui_progress'].append({
                        'method': method,
                        'params': data.get('params', {})
                    })
                    pattern['sequence'].append(('ui', method))
        
        pattern['code_template'] = self._build_download_code(pattern)
        
        return pattern
    
    def _extract_menu_pattern(self, events):
        """Extract menu structure pattern"""
        pattern = {
            'type': 'menu',
            'items': [],
            'structure': defaultdict(list),
            'navigation_flow': [],
            'count': 0
        }
        
        for event in events:
            data = event.get('data', {})
            
            if event['module'] == 'runtime':
                func = data.get('function', '')
                module = data.get('module', '')
                
                if any(x in func.lower() for x in ['menu', 'directory', 'list', 'item']):
                    pattern['items'].append({
                        'function': func,
                        'module': module,
                        'args': data.get('args', '')[:200]
                    })
                    pattern['structure'][module].append(func)
                    pattern['count'] += 1
            
            if event['module'] == 'ui':
                method = data.get('method', '')
                if method == 'select':
                    params = data.get('params', {})
                    pattern['navigation_flow'].append({
                        'heading': params.get('heading', ''),
                        'options': params.get('options', []),
                        'selection': params.get('result')
                    })
        
        pattern['structure'] = dict(pattern['structure'])
        
        return pattern
    
    def _extract_api_pattern(self, events):
        """Extract API usage patterns"""
        pattern = {
            'type': 'api',
            'endpoints': defaultdict(lambda: {'methods': set(), 'calls': 0}),
            'domains': set(),
            'url_patterns': []
        }
        
        for event in events:
            if event['module'] == 'network':
                data = event.get('data', {})
                domain = data.get('domain', '')
                path = data.get('path', '')
                method = data.get('method', 'GET')
                
                if domain:
                    pattern['domains'].add(domain)
                    pattern['endpoints'][domain]['methods'].add(method)
                    pattern['endpoints'][domain]['calls'] += 1
                    
                    # Extract URL pattern
                    if path:
                        # Replace IDs with placeholders
                        pattern_path = re.sub(r'/\d+', '/{id}', path)
                        pattern_path = re.sub(r'=[^&]+', '={value}', pattern_path)
                        if pattern_path not in pattern['url_patterns']:
                            pattern['url_patterns'].append(pattern_path)
        
        # Convert sets to lists for JSON serialization
        for domain in pattern['endpoints']:
            pattern['endpoints'][domain]['methods'] = list(pattern['endpoints'][domain]['methods'])
        pattern['domains'] = list(pattern['domains'])
        
        return pattern
    
    def _extract_auth_pattern(self, events):
        """Extract authentication patterns"""
        pattern = {
            'type': 'auth',
            'login_calls': [],
            'token_usage': [],
            'headers': []
        }
        
        auth_keywords = ['login', 'auth', 'token', 'session', 'credential', 'password']
        
        for event in events:
            data = event.get('data', {})
            
            # Check network calls
            if event['module'] == 'network':
                url = data.get('url', '').lower()
                if any(k in url for k in auth_keywords):
                    pattern['login_calls'].append({
                        'url': data.get('url'),
                        'method': data.get('method'),
                        'status': data.get('status')
                    })
                
                # Check headers for auth tokens
                headers = data.get('headers', {})
                for key, value in headers.items():
                    if any(k in key.lower() for k in ['auth', 'token', 'session']):
                        pattern['headers'].append({
                            'header': key,
                            'value': str(value)[:50] + '...' if len(str(value)) > 50 else value
                        })
            
            # Check DB for auth data
            if event['module'] == 'db':
                sql = data.get('sql', '').lower()
                if any(k in sql for k in auth_keywords):
                    pattern['token_usage'].append({
                        'sql': data.get('sql'),
                        'operation': data.get('operation')
                    })
        
        return pattern
    
    def _extract_all_patterns(self, events):
        """Extract all pattern types"""
        return {
            'favorites': self._extract_favorites_pattern(events),
            'download': self._extract_download_pattern(events),
            'menu': self._extract_menu_pattern(events),
            'api': self._extract_api_pattern(events),
            'auth': self._extract_auth_pattern(events),
            'summary': {
                'total_events': len(events),
                'modules_used': list(set(e['module'] for e in events)),
                'time_range': self._get_time_range(events)
            }
        }
    
    def _build_favorites_code(self, pattern):
        """Generate reusable code from favorites pattern"""
        code = []
        
        if pattern['db_operations']:
            db = pattern['db_operations'][0]
            code.append("# Favorites DB operation")
            code.append(f"cursor.execute(\"{db['sql']}\", {db['params']})")
            code.append("conn.commit()")
        
        if pattern['ui_feedback']:
            ui = pattern['ui_feedback'][0]
            code.append("# User feedback")
            code.append(f"xbmcgui.Dialog().{ui['method']}('{ui['heading']}', '{ui['message']}')")
        
        return code
    
    def _build_download_code(self, pattern):
        """Generate reusable code from download pattern"""
        code = [
            "# Download flow implementation",
            "import urllib.request",
            "import xbmcgui",
            "import xbmcvfs",
            ""
        ]
        
        if pattern['network_calls']:
            code.append("# Download file")
            code.append("url = \"{url}\"".format(url=pattern['network_calls'][0]['url'][:50] + '...'))
            code.append("local_path = xbmcvfs.translatePath('special://temp/download.file')")
            code.append("urllib.request.urlretrieve(url, local_path)")
        
        if pattern['ui_progress']:
            code.append("# Show progress")
            code.append("progress = xbmcgui.DialogProgress()")
            code.append("progress.create('Downloading...')")
        
        return '\n'.join(code)
    
    def _get_time_range(self, events):
        """Get time range of events"""
        if not events:
            return None
        
        times = [e.get('data', {}).get('time', '') for e in events if e.get('data', {}).get('time')]
        if times:
            return {
                'start': min(times),
                'end': max(times)
            }
        return None
    
    def compare_sessions(self, session_1_events, session_2_events):
        """Compare two sessions and identify differences"""
        comparison = {
            'event_counts': {
                'session_1': len(session_1_events),
                'session_2': len(session_2_events)
            },
            'modules_used': {
                'session_1': list(set(e['module'] for e in session_1_events)),
                'session_2': list(set(e['module'] for e in session_2_events))
            },
            'differences': [],
            'similarities': []
        }
        
        # Compare patterns
        patterns_1 = self._extract_all_patterns(session_1_events)
        patterns_2 = self._extract_all_patterns(session_2_events)
        
        # Find differences
        for key in ['favorites', 'download', 'menu']:
            p1 = patterns_1.get(key, {})
            p2 = patterns_2.get(key, {})
            
            if p1.get('count', 0) != p2.get('count', 0):
                comparison['differences'].append({
                    'type': key,
                    'session_1_count': p1.get('count', 0),
                    'session_2_count': p2.get('count', 0)
                })
            elif p1.get('count', 0) > 0:
                comparison['similarities'].append({
                    'type': key,
                    'count': p1.get('count', 0)
                })
        
        return comparison