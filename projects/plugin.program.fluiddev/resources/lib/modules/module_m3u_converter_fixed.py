import os
import re
import json
from datetime import datetime
from pathlib import Path


class M3UConverter:
    """M3U/M3U8 to JSON Converter - Kodi optimized paths"""
    
    PATTERNS = {
        'video_id_param': re.compile(r'video_id=([a-zA-Z0-9_-]{11})'),
        'plugin_url': re.compile(r'plugin://plugin\.video\.youtube/play/\?video_id=([a-zA-Z0-9_-]{11})'),
        'youtube_url': re.compile(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'),
        'standalone_id': re.compile(r'^([a-zA-Z0-9_-]{11})$')
    }
    
    def __init__(self, config):
        self.config = config
        self.env = self._detect_environment()
        self.mode = None
        self.results = {}
        
    def _detect_environment(self):
        try:
            import xbmc
            return "kodi"
        except ImportError:
            return "dev"
    
    def run(self):
        self.mode = self._select_mode()
        if not self.mode:
            return
        
        input_dir = self._select_input_directory()
        if not input_dir:
            return
        
        m3u_files = self._find_m3u_files(input_dir)
        if not m3u_files:
            self._notify("No M3U files found", "WARNING")
            return
        
        if self.mode == "fulldev":
            m3u_files = self._select_files(m3u_files)
            if not m3u_files:
                return
        
        self._notify(f"Converting {len(m3u_files)} file(s)...", "INFO")
        
        for filepath in m3u_files:
            self.results[filepath.name] = self._convert_single_file(filepath)
        
        self._show_results()
    
    def _select_mode(self):
        options = ["⚡ Quick - Convert all M3U files", "🔧 FullDev - Select specific files"]
        idx = self.config.dialog_select("M3U Converter", options)
        return "quick" if idx == 0 else "fulldev" if idx == 1 else None
    
    def _select_input_directory(self):
        default_path = os.path.join(self.config.profile_path, "playlists")
        os.makedirs(default_path, exist_ok=True)
        
        if self.mode == "quick":
            return Path(default_path)
        
        custom_path = self.config.dialog_input("Playlists directory", default_path)
        return Path(custom_path) if custom_path and os.path.exists(custom_path) else Path(default_path)
    
    def _find_m3u_files(self, directory):
        m3u_files = []
        if directory.is_file() and directory.suffix.lower() in ['.m3u', '.m3u8']:
            m3u_files.append(directory)
        elif directory.is_dir():
            for ext in ['.m3u', '.m3u8']:
                m3u_files.extend(list(directory.glob(f"*{ext}")))
        return sorted(m3u_files)
    
    def _select_files(self, m3u_files):
        if not m3u_files:
            return []
        
        file_names = [f.name for f in m3u_files]
        selected_indices = []
        
        while True:
            remaining = [f for i, f in enumerate(file_names) if i not in selected_indices]
            if not remaining:
                break
            
            idx = self.config.dialog_select(f"Select M3U ({len(selected_indices)} selected)", remaining)
            if idx < 0:
                break
            
            orig_idx = file_names.index(remaining[idx])
            selected_indices.append(orig_idx)
        
        return [m3u_files[i] for i in selected_indices]
    
    def _extract_video_id(self, line):
        line = line.strip()
        for pattern_name, pattern in self.PATTERNS.items():
            match = pattern.search(line)
            if match:
                return match.group(1), pattern_name
        return None, None
    
    def _parse_m3u_file(self, filepath):
        videos = []
        current_title = ""
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#EXTCPlayListM3U::"):
                    continue
                
                if line.startswith("#EXTINF"):
                    if "," in line:
                        current_title = line.split(",", 1)[1].strip()
                    elif ":" in line:
                        current_title = line.split(":", 1)[1].strip()
                    else:
                        current_title = line.replace("#EXTINF", "").strip()
                    continue
                
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
        videos = self._parse_m3u_file(filepath)
        
        if not videos:
            return {"status": "warning", "message": "No videos found", "count": 0}
        
        # FIXED: Kodi-specific path
        output_dir = Path(self.config.profile_path) / "m3u2json"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        json_filename = filepath.stem + ".json"
        json_path = output_dir / json_filename
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "source_file": filepath.name,
                    "count": len(videos),
                    "playlists": videos
                }, f, indent=2, ensure_ascii=False)
            
            return {"status": "success", "output_file": str(json_path), "count": len(videos)}
        except Exception as e:
            return {"status": "error", "message": str(e), "count": 0}
    
    def _show_results(self):
        total = len(self.results)
        success = sum(1 for r in self.results.values() if r.get("status") == "success")
        total_videos = sum(r.get("count", 0) for r in self.results.values())
        
        summary = f"Files: {total}\nSuccess: {success}\nVideos: {total_videos}"
        self.config.dialog_ok("Complete", f"✅ {summary}")
    
    def _notify(self, message, icon="INFO"):
        if self.env == "kodi":
            self.config.notification("M3U Converter", message, icon)
