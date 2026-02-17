import os

class CallLogger:
    def __init__(self, config):
        self.config = config
        self.sources = {}
        
    def register_source(self, name, module):
        self.sources[name] = module
    
    def get_logs(self, log_type='all', addon_filter=None):
        all_logs = []
        
        if log_type == 'all' or log_type == 'runtime':
            all_logs.extend(self._get_from_source('runtime'))
        
        if log_type == 'all' or log_type == 'ui':
            all_logs.extend(self._get_from_source('ui'))
        
        if log_type == 'all' or log_type == 'db':
            all_logs.extend(self._get_from_source('db'))
        
        if log_type == 'all' or log_type == 'network':
            all_logs.extend(self._get_from_source('network'))
        
        all_logs.sort(key=lambda x: x.get('time', ''))
        
        if addon_filter:
            all_logs = [l for l in all_logs if addon_filter in str(l)]
        
        return self._format_for_display(all_logs)
    
    def _get_from_source(self, source):
        logs = []
        log_dir = self.config.logs_path
        
        if not os.path.exists(log_dir):
            return logs
        
        for filename in os.listdir(log_dir):
            if filename.startswith(source) and filename.endswith('.json'):
                data = self.config.load_json(filename)
                if data:
                    logs.extend(data if isinstance(data, list) else [data])
        
        return logs
    
    def _format_for_display(self, logs):
        formatted = []
        
        for log in logs:
            entry = {
                'summary': self._create_summary(log),
                'details': self._create_details(log),
                'raw': log
            }
            formatted.append(entry)
        
        return formatted
    
    def _create_summary(self, log):
        log_type = log.get('type', 'unknown')
        time = log.get('time', '')[:19]
        
        if log_type == 'ui_dialog':
            method = log.get('method', '')
            heading = log.get('params', {}).get('heading', '')
            return f"[{time}] UI: {method} - {heading}"
        
        elif log_type == 'db_query':
            op = log.get('operation', '')
            db = os.path.basename(log.get('database', ''))
            return f"[{time}] DB: {op} on {db}"
        
        elif log_type == 'network':
            method = log.get('method', '')
            url = log.get('url', '')[:50]
            status = log.get('status', '')
            return f"[{time}] NET: {method} {url}... [{status}]"
        
        else:
            module = log.get('module', '')
            func = log.get('function', '')
            return f"[{time}] {module}.{func}"
    
    def _create_details(self, log):
        lines = []
        
        for key, value in log.items():
            if key == 'time':
                continue
            lines.append(f"{key}: {value}")
        
        return '\n'.join(lines)
    
    def export_timeline(self, filename='timeline.txt'):
        logs = self.get_logs()
        
        lines = ["FluidSnoop Timeline Export", "=" * 50, ""]
        
        for log in logs:
            lines.append(log['summary'])
            lines.append("")
        
        path = os.path.join(self.config.exports_path, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return path
