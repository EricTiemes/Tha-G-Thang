import os
import time
import xbmcvfs

from core.config import config
from core.database import db
from core.kodi_utils import kodi
from core.logger import logger

class FluidDownloader:
    """
    Main download orchestrator
    Supports: background/manual download, privacy mode, termux fallback
    """
    
    QUALITY_PRESETS = {
        '360p': {'format': 'best[height<=360]', 'ext': 'mp4'},
        '480p': {'format': 'best[height<=480]', 'ext': 'mp4'},
        '720p': {'format': 'best[height<=720]', 'ext': 'mp4'},
        '1080p': {'format': 'best[height<=1080]', 'ext': 'mp4'},
        'best': {'format': 'best', 'ext': 'mp4'},
        'mp3': {'format': 'bestaudio/best', 'ext': 'mp3', 'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]},
        'mp3_boost': {'format': 'bestaudio/best', 'ext': 'mp3', 'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'},
            {'key': 'FFmpegNormalize'}
        ]}
    }
    
    def __init__(self):
        self.download_path = self._get_download_path()
        self.yt_dlp_available = self._check_yt_dlp()
    
    def _get_download_path(self):
        """Get configured download path"""
        if config.is_simple_mode:
            path = config.get_setting('simple_download_path', 'special://temp/fluid')
        else:
            path = config.get_setting('download_path', 'special://temp/fluid')
        return kodi.get_valid_path(path)
    
    def _check_yt_dlp(self):
        """Check if yt-dlp is available"""
        try:
            import yt_dlp  # noqa: F401
            return True
        except ImportError:
            return False
    
    def quick_download(self, video_info=None):
        """
        Quick download with default settings
        Uses background or manual based on config
        """
        if not video_info:
            video_info = kodi.get_current_video()
        
        if not video_info:
            kodi.notify('No video playing', level='warning')
            return False
        
        quality = self._get_default_quality()
        
        if config.download_mode == 'background':
            return self._start_background_download(video_info, quality)
        else:
            return self._download_manual(video_info, quality)
    
    def download_with_options(self, video_info=None):
        """
        Manual download with user selection
        Always interactive regardless of download_mode setting
        """
        if not video_info:
            video_info = kodi.get_current_video()
        
        if not video_info:
            kodi.notify('No video playing', level='warning')
            return False
        
        # Select quality
        qualities = list(self.QUALITY_PRESETS.keys())
        q_choice = kodi.dialog_select('Select Quality', qualities)
        if q_choice < 0:
            return False
        
        quality = qualities[q_choice]
        
        # Privacy option in advanced mode
        privacy_mode = False
        if config.is_advanced_mode and config.privacy_timestamp_rename:
            privacy_choice = kodi.dialog_yesno(
                'Privacy Mode',
                'Use timestamp filename for privacy?'
            )
            privacy_mode = privacy_choice
        
        return self._download_manual(video_info, quality, privacy_mode)
    
    def _get_default_quality(self):
        """Get default quality from settings"""
        if config.is_simple_mode:
            return config.get_setting('simple_quality', '720p')
        return config.get_setting('default_quality', '720p')
    
    def _start_background_download(self, video_info, quality):
        """Queue download for background processing"""
        try:
            video_id = self._extract_video_id(video_info['url'])
            
            # Add to database
            download_id = db.add_download(
                video_id=video_id,
                url=video_info['url'],
                title=video_info['title'],
                quality=quality
            )
            
            if download_id:
                kodi.notify(f'Download queued: {video_info["title"][:30]}...')
                
                # Start service if not running
                self._ensure_service_running()
                return True
            
        except Exception as e:
            logger.error(f"Background download error: {e}")
            kodi.notify('Failed to queue download', level='error')
        
        return False
    
    def _download_manual(self, video_info, quality, privacy_mode=False):
        """
        Execute download immediately with progress
        Returns local path on success
        """
        url = video_info['url']
        title = video_info['title']
        
        if not self.yt_dlp_available:
            # Try termux fallback
            if config.get_setting('termux_fallback', False):
                return self._termux_fallback_download(url, quality)
            else:
                kodi.notify('yt-dlp not available', level='error')
                return False
        
        try:
            import yt_dlp
            
            # Prepare filename
            if privacy_mode or config.privacy_timestamp_rename:
                filename = f"{int(time.time())}"
            else:
                filename = kodi.sanitize_filename(title)
            
            # Ensure download directory exists
            if not xbmcvfs.exists(self.download_path):
                xbmcvfs.mkdirs(self.download_path)
            
            # yt-dlp options
            ydl_opts = {
                'format': self.QUALITY_PRESETS[quality]['format'],
                'outtmpl': os.path.join(self.download_path, f'{filename}.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
            }
            
            # Add postprocessors for audio
            if 'postprocessors' in self.QUALITY_PRESETS[quality]:
                ydl_opts['postprocessors'] = self.QUALITY_PRESETS[quality]['postprocessors']
            
            # Privacy: strip metadata
            if privacy_mode or config.privacy_strip_exif:
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegMetadata',
                    'add_metadata': False
                })
            
            # Progress dialog
            dialog = kodi.dialog_progress('Downloading...', title)
            
            def progress_hook(d):
                if dialog.iscanceled():
                    raise Exception('Download cancelled')
                
                if d['status'] == 'downloading':
                    percent = d.get('percent', 0)
                    speed = d.get('speed', 0)
                    dialog.update(int(percent), f"Speed: {speed}")
                elif d['status'] == 'finished':
                    dialog.update(100, 'Download complete!')
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            # Execute download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                final_file = ydl.prepare_filename(info)
            
            dialog.close()
            
            # Post-download processing
            self._post_download(final_file, video_info, privacy_mode)
            
            kodi.notify('Download complete!')
            return final_file
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            kodi.notify(f'Download failed: {str(e)}', level='error')
            return False
    
    def _post_download(self, local_file, video_info, privacy_mode):
        """
        Handle delivery after download
        Based on delivery_mode setting
        """
        delivery_mode = config.delivery_mode
        
        if delivery_mode == 'background':
            # Queue for background delivery
            from modules.delivery.router import DeliveryRouter
            router = DeliveryRouter()
            router.queue_delivery(local_file, video_info, privacy_mode)
            kodi.notify('Delivery queued')
            
        elif delivery_mode == 'manual':
            # Ask user what to do
            choice = kodi.dialog_yesno(
                'Download Complete',
                'Deliver to destinations now?',
                nolabel='Keep Local',
                yeslabel='Deliver Now'
            )
            if choice:
                from modules.delivery.router import DeliveryRouter
                router = DeliveryRouter()
                router.deliver_now(local_file, video_info)
                
        else:  # ask
            # Show destination selection
            from modules.delivery.router import DeliveryRouter
            router = DeliveryRouter()
            router.deliver_interactive(local_file, video_info)
        
        # Auto-favorite
        if config.is_simple_mode:
            auto_fav = config.get_setting('simple_auto_favorite', False)
        else:
            auto_fav = config.get_setting('auto_favorite', False)
        
        if auto_fav:
            from modules.favorites.manager import FavoritesManager
            fav = FavoritesManager()
            fav.add_from_video(video_info, privacy_mode=privacy_mode)
    
    def _termux_fallback(self, url, quality):
        """Fallback to Termux for downloading"""
        try:
            import subprocess
            
            # Create intent to start Termux with URL
            cmd = [
                'am', 'startservice',
                '--user', '0',
                '-n', 'com.termux/com.termux.app.TermuxService',
                '-a', 'com.termux.service_execute',
                '-d', 'com.termux.execute.path/home/termux/bin/fluid-bridge.sh',
                '--es', 'com.termux.execute.arguments', url
            ]
            
            subprocess.Popen(cmd)
            kodi.notify('Handed to Termux')
            return True
            
        except Exception as e:
            logger.error(f"Termux fallback error: {e}")
            return False
    
    def _extract_video_id(self, url):
        """Extract video ID from URL"""
        import re
        
        # YouTube
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\s?]+)',
            r'(?:vimeo\.com/)(\d+)',
            r'(?:dailymotion\.com/video/)([^\s?]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Fallback: hash the URL
        return hash(url) % 10000000
    
    def _ensure_service_running(self):
        """Ensure background service is active"""
        # Kodi auto-starts services, but we can verify
        pass
    
    def process_url(self, url):
        """Process URL from share or other source"""
        video_info = {
            'url': url,
            'title': 'Shared URL',
            'thumb': ''
        }
        return self.quick_download(video_info)

# Export for module system
__all__ = ['FluidDownloader']


# ---------------------------------------------------------------------------
# Module route registration
# ---------------------------------------------------------------------------

def _handle_downloader_route(params):
    mode = params.get('mode', '')
    dl = FluidDownloader()
    if mode == 'download_current':
        dl.quick_download()
    elif mode == 'download_options':
        dl.download_with_options()


MODULE_ROUTES = {
    'download_current': _handle_downloader_route,
    'download_options': _handle_downloader_route,
}
