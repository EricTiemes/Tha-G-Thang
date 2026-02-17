import sqlite3
import re
from datetime import datetime

class DBSpy:
    """Intercepts and logs database operations"""
    
    def __init__(self, config):
        self.config = config
        self.active = False
        self.original_connect = None
        self.original_cursor = None
        self.session_id = None
        self.target_filter = None
        self.buffer = []
        self.buffer_size = config.get_int('advanced.buffer_size')
        self.monitored_dbs = []
        
    def start(self, session_id=None, target_filter=None):
        """Start database monitoring"""
        if self.active:
            return
        
        self.session_id = session_id
        self.target_filter = target_filter
        self.buffer = []
        self.monitored_dbs = []
        
        # Hook sqlite3.connect
        self.original_connect = sqlite3.connect
        sqlite3.connect = self._wrapped_connect
        
        self.active = True
        self.config.log("DB spy activated")
    
    def stop(self):
        """Stop monitoring and flush buffer"""
        if not self.active:
            return
        
        sqlite3.connect = self.original_connect
        
        self.active = False
        self._flush_buffer()
        self.config.log("DB spy deactivated")
    
    def _wrapped_connect(self, database, *args, **kwargs):
        """Wrap database connections"""
        conn = self.original_connect(database, *args, **kwargs)
        
        # Check if we should monitor this database
        if self._should_monitor(database):
            self.monitored_dbs.append(str(database))
            return self._wrap_connection(conn, database)
        
        return conn
    
    def _should_monitor(self, db_path):
        """Determine if database should be monitored"""
        path_str = str(db_path).lower()
        
        # Always monitor if target filter matches
        if self.target_filter:
            if self.target_filter.lower() in path_str:
                return True
        
        # Monitor common patterns
        patterns = [
            'favorites', 'bookmark', 'settings', 'cache', 
            'metadata', 'addon_data', 'view modes'
        ]
        
        return any(p in path_str for p in patterns)
    
    def _wrap_connection(self, conn, db_path):
        """Wrap connection to intercept cursor creation"""
        spy = self
        original_cursor = conn.cursor
        
        def wrapped_cursor(*args, **kwargs):
            cursor = original_cursor(*args, **kwargs)
            return spy._wrap_cursor(cursor, db_path)
        
        conn.cursor = wrapped_cursor
        
        # Also wrap direct execute
        original_execute = conn.execute
        def wrapped_conn_execute(sql, parameters=()):
            spy._log_query(db_path, sql, parameters, 'connection.execute')
            return original_execute(sql, parameters)
        
        conn.execute = wrapped_conn_execute
        
        return conn
    
    def _wrap_cursor(self, cursor, db_path):
        """Wrap cursor to intercept execute calls"""
        spy = self
        original_execute = cursor.execute
        original_executemany = cursor.executemany
        original_executescript = cursor.executescript
        
        def wrapped_execute(sql, parameters=()):
            spy._log_query(db_path, sql, parameters, 'cursor.execute')
            return original_execute(sql, parameters)
        
        def wrapped_executemany(sql, seq_of_parameters):
            spy._log_query(db_path, sql, f"{len(seq_of_parameters)} rows", 'cursor.executemany')
            return original_executemany(sql, seq_of_parameters)
        
        def wrapped_executescript(sql_script):
            spy._log_query(db_path, sql_script[:200], None, 'cursor.executescript')
            return original_executescript(sql_script)
        
        cursor.execute = wrapped_execute
        cursor.executemany = wrapped_executemany
        cursor.executescript = wrapped_executescript
        
        return cursor
    
    def _log_query(self, db_path, sql, parameters, source):
        """Log database query"""
        entry = {
            'time': datetime.now().isoformat(),
            'type': 'db_query',
            'database': str(db_path),
            'sql': str(sql)[:500],
            'params': str(parameters)[:200] if parameters else None,
            'operation': self._get_operation(sql),
            'source': source
        }
        
        # Extract table names
        tables = self._extract_tables(sql)
        if tables:
            entry['tables'] = tables
        
        self.buffer.append(entry)
        
        if len(self.buffer) >= self.buffer_size:
            self._flush_buffer()
    
    def _get_operation(self, sql):
        """Determine SQL operation type"""
        sql_upper = str(sql).strip().upper()
        operations = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 
                     'DROP', 'ALTER', 'PRAGMA', 'BEGIN', 'COMMIT', 'ROLLBACK']
        
        for op in operations:
            if sql_upper.startswith(op):
                return op
        return 'OTHER'
    
    def _extract_tables(self, sql):
        """Extract table names from SQL"""
        tables = []
        sql_upper = str(sql).upper()
        
        # FROM/JOIN/INTO patterns
        patterns = [
            r'FROM\\s+(\\w+)',
            r'JOIN\\s+(\\w+)',
            r'INTO\\s+(\\w+)',
            r'UPDATE\\s+(\\w+)',
            r'TABLE\\s+(\\w+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, sql_upper)
            tables.extend(matches)
        
        return list(set(tables)) if tables else None
    
    def _flush_buffer(self):
        """Write buffered events to database"""
        if not self.buffer:
            return
        
        from persistence.database import Database
        db = Database(self.config)
        
        for entry in self.buffer:
            db.add_event(
                session_id=self.session_id,
                module='db',
                event_type=entry['operation'],
                data=entry
            )
        
        self.buffer = []
    
    def get_schema(self, db_path):
        """Extract schema from database"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            schema = {}
            for (table_name,) in tables:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                schema[table_name] = [
                    {
                        'name': col[1],
                        'type': col[2],
                        'notnull': col[3],
                        'default': col[4],
                        'pk': col[5]
                    }
                    for col in columns
                ]
            
            conn.close()
            return schema
            
        except Exception as e:
            self.config.log(f"Schema extraction error: {e}", 3)
            return None
    
    def get_stats(self):
        """Get module statistics"""
        operations = {}
        for entry in self.buffer:
            op = entry['operation']
            operations[op] = operations.get(op, 0) + 1
        
        return {
            'active': self.active,
            'buffered': len(self.buffer),
            'monitored_dbs': len(self.monitored_dbs),
            'operations': operations
        }