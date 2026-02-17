# ruff: noqa: E402
import xbmc
import time
import os
import sys

addon_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(addon_path, 'resources', 'lib'))

from core.config import config
from core.logger import logger

class FluidService:
    """
    Background service for:
    - Processing delivery queue
    - Metadata fetching
    - Cleanup tasks
    """
    
    def __init__(self):
        self.monitor = xbmc.Monitor()
        self.running = True
        self.last_delivery_check = 0
        self.last_cleanup = 0
        self.last_share_check = 0
    
    def run(self):
        """Main service loop"""
        logger.info("FLUID service started")
        
        while not self.monitor.abortRequested():
            try:
                current_time = time.time()
                
                # Process download + delivery queues every 30 seconds
                if current_time - self.last_delivery_check > 30:
                    self._process_download_queue()   # downloads first
                    self._process_delivery_queue()   # then deliver completed
                    self.last_delivery_check = current_time
                
                # Cleanup old records every hour
                if current_time - self.last_cleanup > 3600:
                    self._cleanup_old_records()
                    self.last_cleanup = current_time
                
                # Check for shared URLs (Android) - throttled to every 5s
                if config.get_setting('android_share_receiver', False):
                    if current_time - self.last_share_check > 5:
                        self._check_shared_urls()
                        self.last_share_check = current_time
                
            except Exception as e:
                logger.error(f"Service loop error: {e}")
            
            # Wait with abort check
            if self.monitor.waitForAbort(10):
                break
        
        logger.info("FLUID service stopped")
    
    def _process_download_queue(self):
        """
        Pick up queued downloads and execute them via yt-dlp.
        Processes one item per tick to avoid competing with delivery and playback.
        Status: queued -> running -> completed (then delivery queue picks it up)
        """
        try:
            import sqlite3
            from core.database import db
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, url, title, quality
                FROM downloads
                WHERE status = 'queued'
                ORDER BY created_at ASC LIMIT 1
            """)
            row = cursor.fetchone()
            conn.close()

            if not row:
                return

            download_id, url, title, quality = row
            db.update_download_status(download_id, 'running')

            try:
                from modules.downloader.engine import FluidDownloader
                dl = FluidDownloader()
                video_info = {'url': url, 'title': title or 'Unknown', 'thumb': ''}
                # Use quality from DB record
                if quality and quality in dl.QUALITY_PRESETS:
                    dl_quality = quality
                else:
                    dl_quality = dl._get_default_quality()
                local_file = dl._download_manual(video_info, dl_quality)
                if local_file:
                    db.update_download_status(download_id, 'completed', local_path=local_file)
                    # Queue for delivery now that file exists
                    from modules.delivery.router import DeliveryRouter
                    DeliveryRouter().queue_delivery(local_file, video_info)
                else:
                    db.update_download_status(download_id, 'failed', error='Download returned no file')
            except Exception as e:
                logger.error(f"Background download execution error: {e}")
                db.update_download_status(download_id, 'failed', error=str(e))

        except Exception as e:
            logger.error(f"Download queue processing error: {e}")

    def _process_delivery_queue(self):
        """Process pending deliveries"""
        from modules.delivery.router import DeliveryProcessor
        
        try:
            processor = DeliveryProcessor()
            processor.process_pending()
        except Exception as e:
            logger.error(f"Delivery processing error: {e}")
    
    def _cleanup_old_records(self):
        """Clean old download and delivery records via cleaner module."""
        try:
            from core.cleaner import purge_old_records
            counts = purge_old_records()
            logger.debug(f"Cleanup: {counts}")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def _check_shared_urls(self):
        """Check for URLs shared from Android apps"""
        share_file = os.path.join(config.profile_path, '.shared_url')
        
        if os.path.exists(share_file):
            try:
                with open(share_file, 'r') as f:
                    url = f.read().strip()
                
                if url:
                    logger.info(f"Processing shared URL: {url}")
                    from modules.downloader.engine import FluidDownloader
                    dl = FluidDownloader()
                    dl.process_url(url)
                
                # Remove processed file
                os.remove(share_file)
            except Exception as e:
                logger.error(f"Shared URL processing error: {e}")

if __name__ == '__main__':
    service = FluidService()
    service.run()