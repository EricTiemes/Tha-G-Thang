import os
import re
import json
from datetime import datetime
from pathlib import Path


class M3UConverter:
    """
    M3U/M3U8 to JSON Converter for YouTube Playlists
    
    Supports:
    - Quick mode: Auto-convert all M3U files
    - FullDev mode: Select specific files
    - Kodi GUI interface
    """
    
    # Regex patterns for different M3U formats
    PATTERNS = {
        'video_id_param': re.compile(r'video_id=([a-zA-Z0-9_-]{11})'),
        'plugin_url': re.compile(r'plugin://plugin\.video\.youtube/play/\?video_id=([a-zA-Z0-9_-]{11})'),
        'youtube_url': re.compile(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'),
        'standalone_id': re.compile(r'^([a-zA-Z0-9_-]{11})$')
    }
    
    def __init__(self, config):
        """Initialize module."""
        self.config = config
        self.env = self._detect_environment()
        self.mode = None
        self.results = {}
        
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
        """Main entry point - runs interactive mode."""
        self.mode = self._select_mode()
        if not self.mode:
            return
        
        # Get input directory
        input_dir = self._select_input_directory()
        if not input_dir:
            return
        
        # Find M3U files
        m3u_files = self._find_m3u_files(input_dir)
        if not m3u_files:
            self._notify("No M3U files found", "WARNING")
            return
        
        # In FullDev mode, let user select specific files
        if self.mode == "fulldev":
            m3u_files = self._select_files(m3u_files)
            if not m3u_files:
                return
        
        # Convert files
        self._notify(f"Converting {len(m3u_files)} file(s)...", "INFO")
        
        for filepath in m3u_files:
            self.results[filepath.name] = self._convert_single_file(filepath)
        
        self._show_results()
    
    def run_quick(self, input_path):
        """Quick mode API - convert all M3U files."""
        self.mode = "quick"
        input_dir = Path(input_path)
        m3u_files = self._find_m3u_files(input_dir)
        
        for filepath in m3u_files:
            self.results[filepath.name] = self._convert_single_file(filepath)
        
        return self.results
    
    def run_fulldev(self, input_path, file_list=None):
        """FullDev mode API - convert specific files."""
        self.mode = "fulldev"
        input_dir = Path(input_path)
        m3u_files = self._find_m3u_files(input_dir)
        
        if file_list:
            m3u_files = [f for f in m3u_files if f.name in file_list]
        
        for filepath in m3u_files:
            self.results[filepath.name] = self._convert_single_file(filepath)
        
        return self.results
    
    # =========================================================================
    # MODE SELECTION
    # =========================================================================
    
    def _select_mode(self):
        """Ask user: Quick [1] or FullDev [2]."""
        options = [
            "⚡ Quick - Convert all M3U files",
            "🔧 FullDev - Select specific files"
        ]
        idx = self.config.dialog_select("M3U Converter - Select Mode", options)
        
        if idx == 0:
            return "quick"
        elif idx == 1:
            return "fulldev"
        return None
    
    # =========================================================================
    # FILE SELECTION
    # =========================================================================
    
    def _select_input_directory(self):
        """Select directory containing M3U files."""
        # Default paths
        if self.env == "kodi":
            default_path = os.path.join(self.config.profile_path, "playlists")
        else:
            default_path = os.path.expanduser("~/playlists")
        
        # Create if doesn't exist
        os.makedirs(default_path, exist_ok=True)
        
        # In Quick mode, use default
        if self.mode == "quick":
            return Path(default_path)
        
        # In FullDev, allow custom path
        custom_path = self.config.dialog_input("Playlists directory", default_path)
        
        if custom_path and os.path.exists(custom_path):
            return Path(custom_path)
        
        return Path(default_path)
    
    def _find_m3u_files(self, directory):
        """Find all M3U/M3U8 files in directory."""
        m3u_files = []
        
        if directory.is_file() and directory.suffix.lower() in ['.m3u', '.m3u8']:
            m3u_files.append(directory)
        elif directory.is_dir():
            for ext in ['.m3u', '.m3u8']:
                m3u_files.extend(list(directory.glob(f"*{ext}")))
        
        return sorted(m3u_files)
    
    def _select_files(self, m3u_files):
        """Let user select which files to convert."""
        if not m3u_files:
            return []
        
        file_names = [f.name for f in m3u_files]
        
        # Multi-select dialog
        selected_indices = []
        
        while True:
            remaining = [f for i, f in enumerate(file_names) if i not in selected_indices]
            if not remaining:
                break
            
            idx = self.config.dialog_select(
                f"Select M3U file ({len(selected_indices)} selected, Cancel when done)",
                remaining
            )
            
            if idx < 0:
                break
            
            # Find original index
            orig_idx = file_names.index(remaining[idx])
            selected_indices.append(orig_idx)
            self._notify(f"Added: {remaining[idx]}", "INFO")
        
        return [m3u_files[i] for i in selected_indices]
    
    # =========================================================================
    # CORE PROCESSING
    # =========================================================================
    
    def _extract_video_id(self, line):
        """Extract video ID from M3U line. Returns (video_id, line_type)."""
        line = line.strip()
        
        for pattern_name, pattern in self.PATTERNS.items():
            match = pattern.search(line)
            if match:
                return match.group(1), pattern_name
        
        return None, None
    
    def _parse_m3u_file(self, filepath):
        """Parse M3U file and extract video information."""
        videos = []
        current_title = ""
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines and headers
                if not line or line.startswith("#EXTCPlayListM3U::"):
                    continue
                
                # Extract title from EXTINF line
                if line.startswith("#EXTINF"):
                    if "," in line:
                        current_title = line.split(",", 1)[1].strip()
                    elif ":" in line:
                        current_title = line.split(":", 1)[1].strip()
                    else:
                        current_title = line.replace("#EXTINF", "").strip()
                    continue
                
                # Try to extract video ID
                video_id, line_type = self._extract_video_id(line)
                
                if video_id:
                    if not current_title:
                        current_title = f"Video {video_id}" if line_type == 'standalone_id' else line[:100]
                    
                    videos.append({
                        "id": video_id,
                        "title": current_title,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "source_file": filepath.name,
                        "line_type": line_type
                    })
                    
                    current_title = ""
        
        except Exception as e:
            self.config.log(f"Error parsing {filepath.name}: {e}", 3)
        
        return videos
    
    def _convert_single_file(self, filepath):
        """Convert a single M3U file to JSON."""
        videos = self._parse_m3u_file(filepath)
        
        if not videos:
            return {
                "status": "warning",
                "message": "No valid videos found",
                "count": 0
            }
        
        # Create output directory
        if self.env == "kodi":
            output_dir = Path(self.config.profile_path) / "youtube"
        else:
            output_dir = Path.home() / "downloads" / "youtube"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create output filename
        json_filename = filepath.stem + ".json"
        json_path = output_dir / json_filename
        
        # Save as JSON
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "source_file": filepath.name,
                    "count": len(videos),
                    "playlists": videos
                }, f, indent=2, ensure_ascii=False)
            
            return {
                "status": "success",
                "output_file": str(json_path),
                "count": len(videos)
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "count": 0
            }
    
    # =========================================================================
    # OUTPUT & REPORTING
    # =========================================================================
    
    def _show_results(self):
        """Display results in Kodi dialog."""
        total = len(self.results)
        success = sum(1 for r in self.results.values() if r.get("status") == "success")
        total_videos = sum(r.get("count", 0) for r in self.results.values())
        errors = total - success
        
        summary = f"Files: {total}\nSuccess: {success}\nErrors: {errors}\nTotal Videos: {total_videos}"
        
        icon = "✅" if errors == 0 else "⚠️"
        self.config.dialog_ok("Conversion Complete", f"{icon} {summary}")
    
    def _notify(self, message, icon="INFO"):
        """Show notification."""
        if self.env == "kodi":
            self.config.notification("M3U Converter", message, icon)


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
        
        def dialog_input(self, heading, default=""):
            result = input(f"{heading} [{default}]: ")
            return result if result else default
        
        def dialog_ok(self, heading, message):
            print(f"\n{heading}\n{message}")
        
        def notification(self, title, message, icon="INFO"):
            print(f"[{icon}] {title}: {message}")
        
        def log(self, message, level=1):
            print(f"LOG: {message}")
    
    config = StandaloneConfig()
    module = M3UConverter(config)
    module.run()
