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
    """
    YouTube Transcript Downloader with Summaries
    
    Supports:
    - Quick mode: Download all transcripts
    - FullDev mode: Select specific videos
    - Kodi GUI interface
    - Auto-generates summaries
    - Processing time estimates
    """
    
    def __init__(self, config):
        """Initialize module."""
        self.config = config
        self.env = self._detect_environment()
        self.mode = None
        self.results = {}
        self.output_path = None
        
    def _detect_environment(self):
        """Detect if running in Kodi or Dev environment."""
        try:
            import xbmc
            return "kodi"
        except ImportError:
            return "dev"
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def run(self):
        """Main entry point."""
        if not YTA_AVAILABLE:
            self.config.dialog_ok("Error", "youtube-transcript-api not installed")
            return
        
        self.mode = self._select_mode()
        if not self.mode:
            return
        
        # Select JSON file
        playlist_file = self._select_playlist_file()
        if not playlist_file:
            return
        
        # Load videos
        videos = self._load_playlist_data(playlist_file)
        if not videos:
            return
        
        # In FullDev, let user select specific videos
        if self.mode == "fulldev":
            videos = self._select_videos(videos)
            if not videos:
                return
        
        # Set output path
        self.output_path = self._get_output_path()
        
        # Show estimate
        est_time = len(videos) * 2.5  # ~2.5 seconds per video
        confirm = self.config.dialog_yesno(
            "Download Transcripts",
            f"Videos: {len(videos)}\nEstimated time: {int(est_time)} seconds\n\nProceed?"
        )
        
        if not confirm:
            return
        
        # Download
        self._notify(f"Downloading {len(videos)} transcripts...", "INFO")
        
        for idx, video in enumerate(videos, 1):
            self._notify(f"Processing {idx}/{len(videos)}: {video['title'][:30]}...", "INFO")
            self.results[video['title']] = self._download_transcript(video)
        
        # Generate summary
        self._generate_summary()
        
        self._show_results()
    
    def run_quick(self, playlist_file):
        """Quick mode API."""
        self.mode = "quick"
        self.output_path = self._get_output_path()
        
        videos = self._load_playlist_data(playlist_file)
        for video in videos:
            self.results[video['title']] = self._download_transcript(video)
        
        self._generate_summary()
        return self.results
    
    def run_fulldev(self, playlist_file, video_ids=None):
        """FullDev mode API."""
        self.mode = "fulldev"
        self.output_path = self._get_output_path()
        
        videos = self._load_playlist_data(playlist_file)
        
        if video_ids:
            videos = [v for v in videos if v['id'] in video_ids]
        
        for video in videos:
            self.results[video['title']] = self._download_transcript(video)
        
        self._generate_summary()
        return self.results
    
    # =========================================================================
    # MODE SELECTION
    # =========================================================================
    
    def _select_mode(self):
        """Select mode."""
        options = [
            "⚡ Quick - Download all videos",
            "🔧 FullDev - Select specific videos"
        ]
        idx = self.config.dialog_select("Transcript Downloader - Select Mode", options)
        
        if idx == 0:
            return "quick"
        elif idx == 1:
            return "fulldev"
        return None
    
    # =========================================================================
    # FILE & VIDEO SELECTION
    # =========================================================================
    
    def _select_playlist_file(self):
        """Select playlist JSON file."""
        if self.env == "kodi":
            youtube_dir = Path(self.config.profile_path) / "youtube"
        else:
            youtube_dir = Path.home() / "downloads" / "youtube"
        
        if not youtube_dir.exists():
            self.config.dialog_ok("Error", "No playlist files found")
            return None
        
        json_files = sorted([f for f in youtube_dir.glob("*.json")])
        
        if not json_files:
            self.config.dialog_ok("Error", "No playlist files found")
            return None
        
        # Show file list with metadata
        file_info = []
        for f in json_files:
            try:
                with open(f, 'r') as fp:
                    data = json.load(fp)
                    count = data.get('count', len(data.get('playlists', [])))
                    file_info.append(f"{f.name} ({count} videos)")
            except:
                file_info.append(f.name)
        
        idx = self.config.dialog_select("Select Playlist File", file_info)
        
        if idx < 0:
            return None
        
        return json_files[idx]
    
    def _select_videos(self, videos):
        """Let user select specific videos."""
        if not videos:
            return []
        
        video_titles = [f"[{i+1}] {v['title'][:60]}" for i, v in enumerate(videos)]
        
        selected_indices = []
        
        while True:
            remaining = [t for i, t in enumerate(video_titles) if i not in selected_indices]
            if not remaining:
                break
            
            idx = self.config.dialog_select(
                f"Select Video ({len(selected_indices)} selected, Cancel when done)",
                remaining
            )
            
            if idx < 0:
                break
            
            # Find original index
            orig_idx = video_titles.index(remaining[idx])
            selected_indices.append(orig_idx)
            self._notify(f"Added: {videos[orig_idx]['title'][:30]}", "INFO")
        
        return [videos[i] for i in selected_indices]
    
    def _get_output_path(self):
        """Get output directory path."""
        if self.env == "kodi":
            path = Path(self.config.profile_path) / "transcripts"
        else:
            path = Path.home() / "downloads" / "transcripts"
        
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    # =========================================================================
    # CORE PROCESSING
    # =========================================================================
    
    def _load_playlist_data(self, filepath):
        """Load playlist data from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('playlists', [])
        except Exception as e:
            self.config.log(f"Failed to load {filepath}: {e}", 3)
            return []
    
    def _download_transcript(self, video):
        """Download transcript for a video."""
        try:
            video_id = video['id']
            
            # Get transcript
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            
            # Save transcript
            output_file = self._save_transcript(video, transcript)
            
            # Generate summary
            summary_file = self._save_summary(video, transcript)
            
            return {
                "status": "success",
                "video_id": video_id,
                "output_file": str(output_file),
                "summary_file": str(summary_file),
                "lines": len(transcript)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "video_id": video.get('id', 'unknown')
            }
    
    def _save_transcript(self, video, transcript):
        """Save full transcript to file."""
        safe_title = self._sanitize_filename(video['title'])
        filename = f"{video['id']}_{safe_title}.txt"
        filepath = self.output_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Title: {video['title']}\n")
            f.write(f"URL: {video['url']}\n")
            f.write(f"Downloaded: {datetime.now().isoformat()}\n")
            f.write("=" * 70 + "\n\n")
            
            for entry in transcript:
                time_str = self._format_time(entry['start'])
                f.write(f"[{time_str}] {entry['text']}\n")
        
        return filepath
    
    def _save_summary(self, video, transcript):
        """Generate and save transcript summary."""
        safe_title = self._sanitize_filename(video['title'])
        filename = f"{video['id']}_{safe_title}_SUMMARY.txt"
        filepath = self.output_path / filename
        
        # Combine all text
        full_text = " ".join([entry['text'] for entry in transcript])
        
        # Simple summary: first 500 chars + last 500 chars
        summary = ""
        if len(full_text) > 1000:
            summary = full_text[:500] + "\n\n[...]\n\n" + full_text[-500:]
        else:
            summary = full_text
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"SUMMARY: {video['title']}\n")
            f.write("=" * 70 + "\n\n")
            f.write(summary)
            f.write(f"\n\n" + "=" * 70 + "\n")
            f.write(f"Total length: {len(transcript)} segments\n")
            f.write(f"Full transcript: {video['id']}_{safe_title}.txt\n")
        
        return filepath
    
    def _generate_summary(self):
        """Generate processing summary report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_path / f"processing_report_{timestamp}.txt"
        
        total = len(self.results)
        success = sum(1 for r in self.results.values() if r.get("status") == "success")
        errors = total - success
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("YOUTUBE TRANSCRIPT DOWNLOAD REPORT\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Total Videos: {total}\n")
            f.write(f"Successful: {success}\n")
            f.write(f"Failed: {errors}\n\n")
            f.write("=" * 70 + "\n\n")
            
            for title, result in self.results.items():
                status_icon = "✓" if result.get("status") == "success" else "✗"
                f.write(f"{status_icon} {title[:60]}\n")
                if result.get("status") == "error":
                    f.write(f"  Error: {result.get('message', 'Unknown')}\n")
                f.write("\n")
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _sanitize_filename(self, title):
        """Clean filename."""
        safe = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        return safe[:80]
    
    def _format_time(self, seconds):
        """Format seconds to HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    # =========================================================================
    # OUTPUT & REPORTING
    # =========================================================================
    
    def _show_results(self):
        """Display results."""
        total = len(self.results)
        success = sum(1 for r in self.results.values() if r.get("status") == "success")
        errors = total - success
        
        summary = f"Total: {total}\nSuccess: {success}\nErrors: {errors}\n\nOutput: {self.output_path.name}/"
        
        icon = "✅" if errors == 0 else "⚠️"
        self.config.dialog_ok("Download Complete", f"{icon}\n{summary}")
    
    def _notify(self, message, icon="INFO"):
        """Show notification."""
        if self.env == "kodi":
            self.config.notification("Transcript Downloader", message, icon)


# =========================================================================
# STANDALONE ENTRY POINT
# =========================================================================

if __name__ == "__main__":
    class StandaloneConfig:
        def __init__(self):
            self.profile_path = os.path.expanduser("~/.fluiddev")
            os.makedirs(self.profile_path, exist_ok=True)
        
        def dialog_select(self, heading, options):
            print(f"\n{heading}")
            for i, opt in enumerate(options):
                print(f"  [{i}] {opt}")
            try:
                return int(input("Select: "))
            except:
                return -1
        
        def dialog_yesno(self, heading, message):
            print(f"\n{heading}\n{message}")
            return input("Proceed? (y/n): ").lower() == 'y'
        
        def dialog_ok(self, heading, message):
            print(f"\n{heading}\n{message}")
        
        def notification(self, title, message, icon="INFO"):
            print(f"[{icon}] {title}: {message}")
        
        def log(self, message, level=1):
            print(f"LOG: {message}")
    
    config = StandaloneConfig()
    module = YouTubeTranscriptDownloader(config)
    module.run()
