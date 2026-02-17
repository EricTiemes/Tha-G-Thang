import os
import sqlite3
import json
from datetime import datetime

class Database:
    """SQLite persistence for sessions and events"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = os.path.join(config.data_path, 'fluidsnoop.db')
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                research_type TEXT,
                target_addon TEXT,
                modules TEXT,
                formats TEXT,
                status TEXT DEFAULT 'active',
                stats TEXT,
                results_path TEXT
            )
        """)
        
        # Events table (for real-time capture)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                module TEXT,
                event_type TEXT,
                data TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        # Comparisons table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comparisons (
                id TEXT PRIMARY KEY,
                session_1_id TEXT,
                session_2_id TEXT,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                report_path TEXT,
                FOREIGN KEY (session_1_id) REFERENCES sessions(id),
                FOREIGN KEY (session_2_id) REFERENCES sessions(id)
            )
        """)
        
        # Indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)')
        
        conn.commit()
        conn.close()
    
    def create_session(self, session_id, research_type, target_addon, modules, formats):
        """Create new research session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sessions (id, research_type, target_addon, modules, formats, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (session_id, research_type, target_addon, json.dumps(modules), json.dumps(formats)))
        
        conn.commit()
        conn.close()
        return session_id
    
    def update_session(self, session_id, **kwargs):
        """Update session fields"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        allowed_fields = ['status', 'stats', 'results_path', 'updated']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if 'updated' not in updates:
            updates['updated'] = datetime.now().isoformat()
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [session_id]
        
        cursor.execute(f"""
            UPDATE sessions SET {set_clause} WHERE id = ?
        """, values)
        
        conn.commit()
        conn.close()
    
    def get_session(self, session_id):
        """Get session by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_dict(row)
        return None
    
    def get_recent_sessions(self, limit=10):
        """Get recent sessions"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM sessions 
            ORDER BY created DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row) for row in rows]
    
    def get_active_session(self):
        """Get currently active session"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM sessions 
            WHERE status = 'active' 
            ORDER BY created DESC 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_dict(row)
        return None
    
    def delete_session(self, session_id):
        """Delete session and its events"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM events WHERE session_id = ?', (session_id,))
        cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
        
        conn.commit()
        conn.close()
    
    def add_event(self, session_id, module, event_type, data):
        """Add event to session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO events (session_id, module, event_type, data)
            VALUES (?, ?, ?, ?)
        """, (session_id, module, event_type, json.dumps(data)))
        
        conn.commit()
        conn.close()
    
    def get_events(self, session_id, module=None, event_type=None, limit=None):
        """Get events for session"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM events WHERE session_id = ?'
        params = [session_id]
        
        if module:
            query += ' AND module = ?'
            params.append(module)
        if event_type:
            query += ' AND event_type = ?'
            params.append(event_type)
        
        query += ' ORDER BY timestamp'
        
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row) for row in rows]
    
    def get_event_stats(self, session_id):
        """Get event statistics for session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT module, COUNT(*) as count 
            FROM events 
            WHERE session_id = ?
            GROUP BY module
        """, (session_id,))
        
        module_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("""
            SELECT COUNT(*) FROM events WHERE session_id = ?
        """, (session_id,))
        
        total = cursor.fetchone()[0]
        conn.close()
        
        return {'total': total, 'by_module': module_stats}
    
    def create_comparison(self, comparison_id, session_1_id, session_2_id, report_path):
        """Store comparison record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO comparisons (id, session_1_id, session_2_id, report_path)
            VALUES (?, ?, ?, ?)
        """, (comparison_id, session_1_id, session_2_id, report_path))
        
        conn.commit()
        conn.close()
    
    def cleanup_old_sessions(self, max_age_days):
        """Remove sessions older than specified days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(f"""
            DELETE FROM events WHERE session_id IN (
                SELECT id FROM sessions 
                WHERE created < datetime('now', '-{max_age_days} days')
            )
        """)
        
        cursor.execute(f"""
            DELETE FROM sessions 
            WHERE created < datetime('now', '-{max_age_days} days')
        """)
        
        conn.commit()
        conn.close()
    
    def _row_to_dict(self, row):
        """Convert sqlite row to dictionary"""
        d = dict(row)
        # Parse JSON fields
        for key in ['modules', 'formats', 'stats']:
            if key in d and d[key]:
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    pass
        return d