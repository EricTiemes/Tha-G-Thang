import os
import sys
import json
from datetime import datetime
try:
    from youtube_search import YoutubeSearch
except ImportError:
    YoutubeSearch = None


class YouTubePlaylistSearch:
    """
    YouTube Playlist Search and Selection
    
    Supports:
    - Quick mode: Search and select playlists
    - FullDev mode: Advanced filtering and batch operations
    - Both Kodi GUI and CLI interfaces
    """
    
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
        
        # Get search query
        query = self._get_search_query()
        if not query:
            return
        
        self._notify(f"Searching for: {query}", "INFO")
        self.results = self._search_playlists(query)
        
        if not self.results:
            self._notify("No playlists found", "WARNING")
            return
        
        # Show and select from results
        selected = self._select_from_results()
        if selected:
            self._save_selection(selected)
            self._notify(f"Selected {len(selected)} playlist(s)", "INFO")
    
    def run_quick(self, query):
        """Quick mode API - for programmatic use."""
        self.mode = "quick"
        self.results = self._search_playlists(query)
        return self.results
    
    def run_fulldev(self, query, options=None):
        """FullDev mode API - for programmatic use."""
        self.mode = "fulldev"
        options = options or {}
        self.results = self._search_playlists(query, options)
        return self.results
    
    # =========================================================================
    # MODE SELECTION
    # =========================================================================
    
    def _select_mode(self):
        """Ask user: Quick [1] or FullDev [2]."""
        if self.env == "kodi":
            return self._select_mode_kodi()
        else:
            return self._select_mode_cli()
    
    def _select_mode_kodi(self):
        """Kodi GUI mode selection."""
        options = [
            "⚡ Quick Search - Find playlists quickly",
            "🔧 FullDev Search - Advanced filtering"
        ]
        idx = self.config.dialog_select("Select Mode", options)
        
        if idx == 0:
            return "quick"
        elif idx == 1:
            return "fulldev"
        return None
    
    def _select_mode_cli(self):
        """CLI numbered mode selection."""
        print("\n" + "="*60)
        print("YOUTUBE PLAYLIST SEARCH")
        print("="*60)
        print(f"Environment: {self.env.upper()}")
        print("\n[1] ⚡ Quick Search")
        print("    Fast playlist search")
        print("\n[2] 🔧 FullDev Search")
        print("    Advanced filtering and options")
        print("\n[0] Cancel")
        
        try:
            choice = input("\nSelect [0-2]: ").strip()
            if choice == "1":
                return "quick"
            elif choice == "2":
                return "fulldev"
        except (KeyboardInterrupt, EOFError):
            pass
        return None
    
    # =========================================================================
    # SEARCH FUNCTIONALITY
    # =========================================================================
    
    def _get_search_query(self):
        """Get search query from user."""
        if self.env == "kodi":
            query = self.config.dialog_input("Search for playlists", "")
        else:
            query = input("\nEnter search query: ").strip()
        return query
    
    def _search_playlists(self, query, options=None):
        """Search for YouTube playlists."""
        if not YoutubeSearch:
            self._notify("youtube-search-python not installed", "ERROR")
            return []
        
        try:
            max_results = 10 if self.mode == "quick" else options.get("max_results", 20)
            
            # Search for playlists
            results = YoutubeSearch(f"{query} playlist", max_results=max_results).to_dict()
            
            playlists = []
            for idx, item in enumerate(results, 1):
                playlists.append({
                    "number": idx,
                    "title": item.get("title", ""),
                    "url": f"https://youtube.com{item.get('url_suffix', '')}",
                    "channel": item.get("channel", ""),
                    "duration": item.get("duration", "")
                })
            
            return playlists
            
        except Exception as e:
            self._notify(f"Search failed: {e}", "ERROR")
            return []
    
    def _select_from_results(self):
        """Display numbered results and allow selection."""
        if self.env == "kodi":
            return self._select_from_results_kodi()
        else:
            return self._select_from_results_cli()
    
    def _select_from_results_kodi(self):
        """Kodi GUI selection."""
        options = [
            f"[{p['number']}] {p['title']} - {p['channel']}"
            for p in self.results
        ]
        
        selected_indices = []
        while True:
            idx = self.config.dialog_select("Select Playlist (Cancel when done)", options)
            if idx < 0:
                break
            selected_indices.append(idx)
            self._notify(f"Added: {self.results[idx]['title']}", "INFO")
        
        return [self.results[i] for i in selected_indices]
    
    def _select_from_results_cli(self):
        """CLI numbered selection."""
        print("\n" + "="*60)
        print("SEARCH RESULTS")
        print("="*60)
        
        for playlist in self.results:
            print(f"\n[{playlist['number']}] {playlist['title']}")
            print(f"    Channel: {playlist['channel']}")
            print(f"    URL: {playlist['url']}")
        
        print("\nEnter numbers separated by commas (e.g., 1,3,5)")
        print("Or 'all' to select all")
        
        try:
            selection = input("\nSelect: ").strip().lower()
            
            if selection == "all":
                return self.results
            
            selected_nums = [int(n.strip()) for n in selection.split(",")]
            return [p for p in self.results if p["number"] in selected_nums]
            
        except (ValueError, KeyboardInterrupt, EOFError):
            return []
    
    def _save_selection(self, selected):
        """Save selected playlists to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"youtube_playlists_{timestamp}.json"
        
        if self.env == "kodi":
            output_dir = os.path.join(self.config.profile_path, "youtube")
        else:
            output_dir = os.path.expanduser("~/downloads/youtube")
        
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": timestamp,
                "count": len(selected),
                "playlists": selected
            }, f, indent=2)
        
        self._notify(f"Saved to: {filepath}", "INFO")
        return filepath
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _notify(self, message, icon="INFO"):
        """Show notification."""
        if self.env == "kodi":
            self.config.notification("YouTube Search", message, icon)
        else:
            prefix = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}.get(icon, "ℹ️")
            print(f"{prefix} {message}")


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
            print(f"{heading}: ", end="")
            result = input()
            return result if result else default
        
        def notification(self, title, message, icon="INFO"):
            print(f"\n[{icon}] {title}: {message}")
    
    config = StandaloneConfig()
    module = YouTubePlaylistSearch(config)
    module.run()
