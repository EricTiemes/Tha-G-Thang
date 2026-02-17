import os
import json
from datetime import datetime
from pathlib import Path

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    YTA_AVAILABLE = True
except ImportError:
    YTA_AVAILABLE = False


class YouTubeTranscriptDownloader:
    """YouTube Transcript Downloader - Android/Kodi downloads folder"""
    
    def __init__(self, config):
        self.config = config
        self.env = self._detect_environment()
        self.mode = None
        self.results = {}
        self.output_path = None
        
    def _detect_environment(self):
        try:
            import xbmc
            return "kodi"
        except ImportError:
            return "dev"
    
    def run(self):
        if not YTA_AVAILABLE:
            self.config.dialog_ok("Error", "youtube-transcript-api not installed")
            return
        
        self.mode = self._select_mode()
        if not self.mode:
            return
        
        playlist_file = self._select_playlist_file()
        if not playlist_file:
            return
        
        videos = self._load_playlist_data(playlist_file)
        if not videos:
            return
        
        if self.mode == "fulldev":
            videos = self._select_videos(videos)
            if not videos:
                return
        
        self.output_path = self._get_output_path()
        
        est_time = len(videos) * 2.5
        if not self.config.dialog_yesno("Download", f"Videos: {len(videos)}\nTime: ~{int(est_time)}s\nProceed?"):
            return
        
        for idx, video in enumerate(videos, 1):
            self._notify(f"{idx}/{len(videos)}: {video['title'][:30]}...", "INFO")
            self.results[video['title']] = self._download_transcript(video)
        
        self._generate_summary()
        self._show_results()
    
    def _select_mode(self):
        options = ["⚡ Quick - All videos", "🔧 FullDev - Select videos"]
        idx = self.config.dialog_select("Transcript Downloader", options)
        return "quick" if idx == 0 else "fulldev" if idx == 1 else None
    
    def _select_playlist_file(self):
        json_dir = Path(self.config.profile_path) / "m3u2json"
        if not json_dir.exists():
            self.config.dialog_ok("Error", "No playlists found")
            return None
        
        json_files = sorted([f for f in json_dir.glob("*.json")])
        if not json_files:
            return None
        
        file_info = []
        for f in json_files:
            try:
                with open(f, 'r') as fp:
                    data = json.load(fp)
                    count = data.get('count', 0)
                    file_info.append(f"{f.name} ({count} videos)")
            except:
                file_info.append(f.name)
        
        idx = self.config.dialog_select("Select Playlist", file_info)
        return json_files[idx] if idx >= 0 else None
    
    def _select_videos(self, videos):
        video_titles = [f"[{i+1}] {v['title'][:60]}" for i, v in enumerate(videos)]
        selected = []
        
        while True:
            remaining = [t for i, t in enumerate(video_titles) if i not in selected]
            if not remaining:
                break
            
            idx = self.config.dialog_select(f"Select ({len(selected)} chosen)", remaining)
            if idx < 0:
                break
            
            selected.append(video_titles.index(remaining[idx]))
        
        return [videos[i] for i in selected]
    
    def _get_output_path(self):
        """FIXED: Platform-specific downloads folder"""
        if self.env == "kodi":
            # Android Termux/Kodi
            android_path = "/storage/emulated/0/Download/transcripts"
            if os.path.exists("/storage/emulated/0"):
                path = Path(android_path)
            else:
                # Desktop Kodi
                path = Path.home() / "Downloads" / "transcripts"
        else:
            path = Path.home() / "downloads" / "transcripts"
        
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def _load_playlist_data(self, filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f).get('playlists', [])
        except:
            return []
    
    def _download_transcript(self, video):
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video['id'])
            output_file = self._save_transcript(video, transcript)
            summary_file = self._save_summary(video, transcript)
            
            return {
                "status": "success",
                "output_file": str(output_file),
                "summary_file": str(summary_file),
                "lines": len(transcript)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _save_transcript(self, video, transcript):
        safe_title = "".join(c for c in video['title'] if c.isalnum() or c in (' ', '-', '_')).strip()[:80]
        filename = f"{video['id']}_{safe_title}.txt"
        filepath = self.output_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Title: {video['title']}\nURL: {video['url']}\n{'='*70}\n\n")
            for entry in transcript:
                h, m, s = int(entry['start']//3600), int((entry['start']%3600)//60), int(entry['start']%60)
                f.write(f"[{h:02d}:{m:02d}:{s:02d}] {entry['text']}\n")
        
        return filepath
    
    def _save_summary(self, video, transcript):
        safe_title = "".join(c for c in video['title'] if c.isalnum() or c in (' ', '-', '_')).strip()[:80]
        filename = f"{video['id']}_{safe_title}_SUMMARY.txt"
        filepath = self.output_path / filename
        
        full_text = " ".join([e['text'] for e in transcript])
        summary = full_text[:500] + "\n\n[...]\n\n" + full_text[-500:] if len(full_text) > 1000 else full_text
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"SUMMARY: {video['title']}\n{'='*70}\n\n{summary}\n\n{'='*70}\n")
            f.write(f"Segments: {len(transcript)}\nFull: {video['id']}_{safe_title}.txt\n")
        
        return filepath
    
    def _generate_summary(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report = self.output_path / f"report_{timestamp}.txt"
        
        total = len(self.results)
        success = sum(1 for r in self.results.values() if r.get("status") == "success")
        
        with open(report, 'w', encoding='utf-8') as f:
            f.write(f"REPORT\n{'='*70}\n\nTotal: {total}\nSuccess: {success}\nFailed: {total-success}\n\n")
            for title, result in self.results.items():
                icon = "✓" if result.get("status") == "success" else "✗"
                f.write(f"{icon} {title[:60]}\n")
    
    def _show_results(self):
        total = len(self.results)
        success = sum(1 for r in self.results.values() if r.get("status") == "success")
        self.config.dialog_ok("Complete", f"✅ {success}/{total} downloaded\nLocation: {self.output_path}")
    
    def _notify(self, message, icon="INFO"):
        if self.env == "kodi":
            self.config.notification("Transcripts", message, icon)
