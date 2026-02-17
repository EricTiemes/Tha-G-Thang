import json
import sqlite3
import re
from core.database import db
from core.kodi_utils import kodi
from core.logger import logger


class TranscriptFetcher:
    """Fetch video transcripts from various sources"""
    
    SOURCES = {
        'youtube': 'youtube_auto',
        'whisper': 'openai_whisper',
        'manual': 'user_uploaded'
    }
    
    def fetch_youtube_transcript(self, video_id):
        """Fetch YouTube auto-captions"""
        try:
            # Try youtube-transcript-api if available
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                return ' '.join([item['text'] for item in transcript_list])
            except ImportError:
                logger.warning("youtube_transcript_api not available")
                return None
        except Exception as e:
            logger.error(f"Transcript fetch failed: {e}")
            return None
    
    def save_transcript(self, video_id, transcript, source='youtube'):
        """Save transcript to database"""
        try:
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO meta_cache (video_id, transcript, cached_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (video_id, transcript))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Save transcript failed: {e}")
            return False


class ThumbnailFetcher:
    """Fetch extra thumbnails and artwork"""
    
    def fetch_youtube_thumbnails(self, video_id):
        """Get all available YouTube thumbnail qualities"""
        thumbs = {
            'maxres': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
            'sd': f'https://img.youtube.com/vi/{video_id}/sddefault.jpg',
            'hq': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
            'mq': f'https://img.youtube.com/vi/{video_id}/mqdefault.jpg',
            'default': f'https://img.youtube.com/vi/{video_id}/default.jpg'
        }
        return thumbs
    
    def fetch_channel_art(self, channel_id):
        """Fetch channel banner/art (future)"""
        pass
    
    def save_thumbnails(self, video_id, thumbs_dict):
        """Save thumbnail URLs to database"""
        try:
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO meta_cache (video_id, extra_thumbs, cached_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (video_id, json.dumps(thumbs_dict)))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Save thumbnails failed: {e}")
            return False


class MetaFetcher:
    """Main metadata orchestrator"""
    
    def __init__(self):
        self.transcript = TranscriptFetcher()
        self.thumbs = ThumbnailFetcher()
    
    def find_extras_for_video(self, video_info):
        """Interactive: Find and save extras for a video"""
        video_id = self._extract_video_id(video_info['url'])
        
        dialog = kodi.dialog_select(
            'Find Extras',
            ['Fetch Transcript', 'Fetch Extra Thumbnails', 'Fetch All', 'View Existing']
        )
        
        if dialog == 0:
            self._fetch_and_save_transcript(video_id)
        elif dialog == 1:
            self._fetch_and_save_thumbs(video_id)
        elif dialog == 2:
            self._fetch_all(video_id)
        elif dialog == 3:
            self._view_existing(video_id)
    
    def _fetch_and_save_transcript(self, video_id):
        """Fetch and save transcript"""
        kodi.notify('Fetching transcript...')
        transcript = self.transcript.fetch_youtube_transcript(video_id)
        
        if transcript:
            self.transcript.save_transcript(video_id, transcript)
            kodi.notify(f'Transcript saved ({len(transcript)} chars)')
        else:
            kodi.notify('No transcript available', level='warning')
    
    def _fetch_and_save_thumbs(self, video_id):
        """Fetch and save thumbnails"""
        kodi.notify('Fetching thumbnails...')
        thumbs = self.thumbs.fetch_youtube_thumbnails(video_id)
        self.thumbs.save_thumbnails(video_id, thumbs)
        kodi.notify(f'{len(thumbs)} thumbnails saved')
    
    def _fetch_all(self, video_id):
        """Fetch all metadata"""
        self._fetch_and_save_transcript(video_id)
        self._fetch_and_save_thumbs(video_id)
    
    def _view_existing(self, video_id):
        """View cached metadata"""
        try:
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT transcript, extra_thumbs, description FROM meta_cache WHERE video_id=?",
                (video_id,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                transcript, thumbs, desc = result
                msg = f"Transcript: {'Yes' if transcript else 'No'}\\n"
                msg += f"Thumbnails: {'Yes' if thumbs else 'No'}\\n"
                msg += f"Description: {'Yes' if desc else 'No'}"
                kodi.dialog_select('Cached Metadata', [msg])
            else:
                kodi.notify('No cached metadata', level='warning')
                
        except Exception as e:
            logger.error(f"View metadata failed: {e}")
    
    def queue_background_fetch(self, url):
        """Queue for background processing"""
        video_id = self._extract_video_id(url)
        
        # Add to service queue (simplified)
        logger.info(f"Queued metadata fetch for {video_id}")
        # In full implementation, add to service task queue
    
    def _extract_video_id(self, url):
        """Extract video ID"""
        match = re.search(r'(?:v=|/)([\\w-]{11})', url)
        return match.group(1) if match else str(hash(url) % 10000000)


def show_meta_menu():
    """Build metadata menu for Kodi UI"""
    import sys
    import xbmcplugin
    import xbmcgui
    from core.kodi_utils import ThemeManager
    
    addon_handle = int(sys.argv[1])
    list_items = []
    
    # Find extras for current video
    item = xbmcgui.ListItem(label=ThemeManager.format_text("🔍 Find Extras for Current", 'accent'))
    item.setArt({'icon': 'DefaultAddonInfoProvider.png'})
    url = f"{sys.argv[0]}?mode=meta_current"
    list_items.append((url, item, False))
    
    # Browse cached metadata
    item = xbmcgui.ListItem(label=ThemeManager.format_text("📚 Browse Cached Metadata", 'text'))
    item.setArt({'icon': 'DefaultFolder.png'})
    url = f"{sys.argv[0]}?mode=meta_browse"
    list_items.append((url, item, True))
    
    # Settings
    item = xbmcgui.ListItem(label=ThemeManager.format_text("⚙️ Metadata Settings", 'text'))
    item.setArt({'icon': 'DefaultAddonProgram.png'})
    url = f"{sys.argv[0]}?mode=meta_settings"
    list_items.append((url, item, False))
    
    xbmcplugin.addDirectoryItems(addon_handle, list_items)
    xbmcplugin.endOfDirectory(addon_handle)


__all__ = ['MetaFetcher', 'show_meta_menu', 'TranscriptFetcher', 'ThumbnailFetcher']