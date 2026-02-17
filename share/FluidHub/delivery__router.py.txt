import os
import xbmcvfs
import shutil

from core.config import config
from core.database import db
from core.kodi_utils import kodi
from core.logger import logger

class DeliveryRouter:
    """
    Intelligent delivery routing based on keywords/categories
    Supports multiple destinations per file
    """
    
    def __init__(self):
        # Delivery paths are Kodi sources — credentials are managed by Kodi
        # via Settings > File Manager > Add Network Location, stored in
        # userdata/passwords.xml. Never store credentials in delivery_rules.
        self.rules = config.get_delivery_rules()
    
    def analyze_content(self, video_info):
        """
        Determine delivery destinations based on:
        1. Title keywords
        2. Category
        3. Manual rules
        Returns list of destination paths
        """
        title = video_info.get('title', '').lower()
        destinations = []
        
        for rule in self.rules:
            keywords = rule.get('keywords', [])
            paths = rule.get('paths', [])
            
            # Check if any keyword matches
            if any(kw.lower() in title for kw in keywords):
                # Use first available path
                for path in paths:
                    real_path = kodi.get_valid_path(path)
                    if self._path_available(real_path, rule.get('protocol', 'local')):
                        destinations.append({
                            'path': real_path,
                            'protocol': rule.get('protocol', 'local'),
                            'name': rule.get('name', 'Unknown')
                        })
                        break
        
        # Fallback to default if no rules matched
        if not destinations:
            default_path = kodi.get_valid_path('special://profile/Downloads')
            destinations.append({
                'path': default_path,
                'protocol': 'local',
                'name': 'Default'
            })
        
        return destinations
    
    def _path_available(self, path, protocol):
        """Check if destination is accessible"""
        if protocol == 'local':
            # Try to create if doesn't exist
            if not xbmcvfs.exists(path):
                xbmcvfs.mkdirs(path)
            return xbmcvfs.exists(path)
        else:
            # For remote protocols, try to list directory
            return xbmcvfs.exists(path)
    
    def queue_delivery(self, local_file, video_info, privacy_mode=False):
        """Queue for background delivery"""
        destinations = self.analyze_content(video_info)
        
        # Get download ID from database
        video_id = self._extract_video_id(video_info['url'])
        
        # Find the download record
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM downloads WHERE video_id=? ORDER BY id DESC LIMIT 1",
            (video_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        download_id = result[0]
        
        # Queue each destination
        for dest in destinations:
            db.queue_delivery(download_id, dest['path'], dest['protocol'])
        
        return True
    
    def deliver_now(self, local_file, video_info):
        """Immediate delivery to all matching destinations"""
        destinations = self.analyze_content(video_info)
        
        dialog = kodi.dialog_progress('Delivering...', 'Copying to destinations')
        
        success_count = 0
        for i, dest in enumerate(destinations):
            dialog.update(int((i / len(destinations)) * 100), f"To: {dest['name']}")
            
            if self._deliver_file(local_file, dest):
                success_count += 1
        
        dialog.close()
        kodi.notify(f'Delivered to {success_count}/{len(destinations)} locations')
        return success_count
    
    def deliver_interactive(self, local_file, video_info):
        """Let user choose destinations interactively"""
        destinations = self.analyze_content(video_info)
        
        options = [f"{d['name']} ({d['path']})" for d in destinations]
        selected = kodi.dialog_multiselect('Select Destinations', options)
        
        if not selected:
            return 0
        
        dialog = kodi.dialog_progress('Delivering...')
        
        success_count = 0
        for i, idx in enumerate(selected):
            dest = destinations[idx]
            dialog.update(int((i / len(selected)) * 100))
            
            if self._deliver_file(local_file, dest):
                success_count += 1
        
        dialog.close()
        kodi.notify(f'Delivered to {success_count} locations')
        return success_count
    
    def _deliver_file(self, local_file, destination):
        """
        Execute file delivery
        Supports: local copy/move, xbmcvfs (SMB/WebDAV), future: SSH, cloud APIs
        """
        try:
            protocol = destination['protocol']
            dest_path = destination['path']
            filename = os.path.basename(local_file)
            dest_file = os.path.join(dest_path, filename)
            
            if protocol == 'local':
                # Local file operation
                if config.get_setting('move_files', False):
                    shutil.move(local_file, dest_file)
                else:
                    shutil.copy2(local_file, dest_file)
                return True
            
            else:
                # Use Kodi's VFS for remote protocols
                success = xbmcvfs.copy(local_file, dest_file)
                
                if success and config.get_setting('delete_after_remote', False):
                    # Remove local after successful remote copy
                    xbmcvfs.delete(local_file)
                
                return success
                
        except Exception as e:
            logger.error(f"Delivery failed to {destination}: {e}")
            return False
    
    def _extract_video_id(self, url):
        """Extract video ID"""
        import re
        match = re.search(r'(?:v=|/)([\w-]{11})', url)
        return match.group(1) if match else hash(url) % 10000000

class DeliveryProcessor:
    """Background delivery processor"""
    
    def process_pending(self):
        """Process pending deliveries from queue"""
        pending = db.get_pending_deliveries()
        
        for task in pending:
            task_id, download_id, dest_path, protocol, local_file = task
            
            if not local_file or not xbmcvfs.exists(local_file):
                logger.warning(f"Local file missing for delivery {task_id}")
                continue
            
            # Attempt delivery
            router = DeliveryRouter()
            dest = {'path': dest_path, 'protocol': protocol, 'name': 'Queued'}
            
            if router._deliver_file(local_file, dest):
                self._mark_delivered(task_id)
                logger.info(f"Delivered {local_file} to {dest_path}")
            else:
                self._increment_retry(task_id)
    
    def _mark_delivered(self, task_id):
        """Mark delivery task as complete"""
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE delivery_queue SET status='delivered' WHERE id=?",
            (task_id,)
        )
        conn.commit()
        conn.close()
    
    def _increment_retry(self, task_id):
        """Increment retry count, mark failed if too many"""
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE delivery_queue SET retry_count=retry_count+1 WHERE id=?",
            (task_id,)
        )
        cursor.execute(
            "UPDATE delivery_queue SET status='failed' WHERE id=? AND retry_count>=3",
            (task_id,)
        )
        conn.commit()
        conn.close()


# ---------------------------------------------------------------------------
# Module route registration
# ---------------------------------------------------------------------------

def _handle_delivery_route(params):
    """Dispatcher for delivery routes."""
    pass   # Delivery has no menu; runs in background via service or engine


MODULE_ROUTES = {}   # No UI routes — delivery is headless

__all__ = ['DeliveryRouter', 'DeliveryProcessor', 'MODULE_ROUTES']
