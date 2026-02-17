import sqlite3
import os
import json
from .config import config
from .logger import logger

class FluidDatabase:
    """
    Central SQLite database for favorites, downloads, and metadata
    Lightweight: stores URLs and IDs, not local files
    """
    
    def __init__(self):
        self.db_path = os.path.join(config.profile_path, 'fluid.db')
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Favorites with privacy support
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT,
                    thumb_url TEXT,
                    source_addon TEXT,
                    category_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_played TIMESTAMP,
                    play_count INTEGER DEFAULT 0,
                    meta_json TEXT,
                    privacy_mode BOOLEAN DEFAULT 0,
                    FOREIGN KEY (category_id) REFERENCES categories(id)
                )
            """)
            
            # Categories (buckets) with obfuscation for private
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    obfuscated_name TEXT,
                    is_private BOOLEAN DEFAULT 0,
                    icon TEXT,
                    sort_order INTEGER DEFAULT 0,
                    export_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Downloads tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT,
                    url TEXT NOT NULL,
                    title TEXT,
                    status TEXT DEFAULT 'queued',
                    local_path TEXT,
                    quality TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_msg TEXT,
                    privacy_mode BOOLEAN DEFAULT 0
                )
            """)
            
            # Delivery queue
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS delivery_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    download_id INTEGER,
                    destination_path TEXT,
                    protocol TEXT DEFAULT 'local',
                    status TEXT DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (download_id) REFERENCES downloads(id)
                )
            """)
            
            # Metadata cache (lightweight)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meta_cache (
                    video_id TEXT PRIMARY KEY,
                    transcript TEXT,
                    extra_thumbs TEXT,
                    description TEXT,
                    duration INTEGER,
                    channel TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Smart playlists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS smart_playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    rules_json TEXT,
                    sort_method TEXT,
                    max_items INTEGER DEFAULT 50,
                    auto_update BOOLEAN DEFAULT 1,
                    last_generated TIMESTAMP
                )
            """)
            
            # Insert default categories
            cursor.execute("""
                INSERT OR IGNORE INTO categories (id, name, is_private, sort_order)
                VALUES (1, 'General', 0, 1), (2, 'Private', 1, 2)
            """)
            
            conn.commit()
            conn.close()
            logger.debug("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
    

    # ── Query helpers ────────────────────────────────────────────────────

    def query(self, sql: str, params: tuple = ()) -> list:
        """SELECT → list of rows. Empty list on error."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()
            return rows
        except Exception as e:
            logger.error(f"DB query failed: {e}  SQL: {sql}")
            return []

    def one(self, sql: str, params: tuple = ()):
        """SELECT → single row or None."""
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: tuple = ()) -> int:
        """INSERT/UPDATE/DELETE → rowcount. -1 on error."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            rowcount = cursor.rowcount
            conn.close()
            return rowcount
        except Exception as e:
            logger.error(f"DB execute failed: {e}  SQL: {sql}")
            return -1

    def executemany(self, sql: str, params_list: list) -> int:
        """Batch INSERT/UPDATE → total rowcount. -1 on error."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.executemany(sql, params_list)
            conn.commit()
            rowcount = cursor.rowcount
            conn.close()
            return rowcount
        except Exception as e:
            logger.error(f"DB executemany failed: {e}")
            return -1

    def add_favorite(self, video_id, url, title=None, thumb_url=None,
                     category_id=1, source_addon=None, privacy_mode=False,
                     yt_meta: dict = None):
        """
        Add or update favorite.
        yt_meta: dict from intelligence.extract_yt_meta() — stored in meta_json.
        view_count stored separately for sorting.
        """
        try:
            meta = {
                'source_addon': source_addon,
                'added_via': 'manual' if not source_addon else 'download',
            }
            if yt_meta:
                meta.update(yt_meta)
            # Use yt_meta thumbnail if better than what we have
            if yt_meta and yt_meta.get('thumbnail') and not thumb_url:
                thumb_url = yt_meta['thumbnail']

            return self.execute("""
                INSERT OR REPLACE INTO favorites
                (video_id, url, title, thumb_url, category_id, source_addon,
                 meta_json, privacy_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (video_id, url, title, thumb_url, category_id, source_addon,
                  json.dumps(meta), privacy_mode)) >= 0
        except Exception as e:
            logger.error(f"Failed to add favorite: {e}")
            return False
    
    def get_favorites(self, category_id=None, limit=100,
                      order_by='created_at DESC'):
        """
        Get favorites.
        order_by examples: 'created_at DESC', 'meta_json->view_count DESC'
        """
        if category_id:
            return self.query(f"""
                SELECT video_id, url, title, thumb_url, created_at
                FROM favorites WHERE category_id=?
                ORDER BY {order_by} LIMIT ?
            """, (category_id, limit))
        return self.query(f"""
            SELECT video_id, url, title, thumb_url, created_at
            FROM favorites ORDER BY {order_by} LIMIT ?
        """, (limit,))
    
    def add_download(self, video_id, url, title=None, quality='best'):
        """Track new download. Returns download_id or None."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO downloads (video_id, url, title, quality, status)
                VALUES (?, ?, ?, ?, 'queued')
            """, (video_id, url, title, quality))
            download_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return download_id
        except Exception as e:
            logger.error(f"Failed to add download: {e}")
            return None
    
    def update_download_status(self, download_id, status,
                              local_path=None, error=None):
        """Update download status."""
        if status == 'completed':
            self.execute("""
                UPDATE downloads
                SET status=?, local_path=?, completed_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (status, local_path, download_id))
        elif error:
            self.execute(
                "UPDATE downloads SET status=?, error_msg=? WHERE id=?",
                (status, error, download_id)
            )
        else:
            self.execute(
                "UPDATE downloads SET status=? WHERE id=?",
                (status, download_id)
            )
    
    def queue_delivery(self, download_id, destination, protocol='local'):
        """Queue file for delivery."""
        return self.execute("""
            INSERT INTO delivery_queue (download_id, destination_path, protocol)
            VALUES (?, ?, ?)
        """, (download_id, destination, protocol)) >= 0
    
    def get_pending_deliveries(self):
        """Get pending delivery tasks."""
        return self.query("""
            SELECT dq.id, dq.download_id, dq.destination_path, dq.protocol, d.local_path
            FROM delivery_queue dq
            JOIN downloads d ON dq.download_id = d.id
            WHERE dq.status = 'pending'
            ORDER BY dq.created_at
        """)

# Global database instance
db = FluidDatabase()