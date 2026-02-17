import os
import sys
import json
from datetime import datetime


class {ModuleName}:
    """
    {ModuleDescription}
    
    Supports:
    - Quick mode: Fast analysis with presets
    - FullDev mode: Detailed configuration
    - Both Kodi GUI and CLI interfaces
    """
    
    def __init__(self, config):
        """
        Initialize module.
        
        Args:
            config: Config object with environment abstraction
        """
        self.config = config
        self.env = self._detect_environment()
        self.mode = None  # 'quick' or 'fulldev'
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
        
        targets = self._select_targets()
        if not targets:
            self._notify("No targets selected", "WARNING")
            return
        
        self._notify(f"Starting {self.__class__.__name__}...", "INFO")
        
        for target in targets:
            self.results[target] = self._process_target(target)
        
        self._show_results()
    
    def run_quick(self, target):
        """Quick mode API - for programmatic use."""
        self.mode = "quick"
        self.results[target] = self._process_target(target)
        return self.results[target]
    
    def run_fulldev(self, targets, options=None):
        """FullDev mode API - for programmatic use."""
        self.mode = "fulldev"
        options = options or {}
        
        for target in targets:
            self.results[target] = self._process_target(target, options)
        
        return self.results
    
    # =========================================================================
    # MODE SELECTION (Universal)
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
            "⚡ Quick Mode - Fast analysis with presets",
            "🔧 FullDev Mode - Detailed configuration"
        ]
        idx = self.config.dialog_select("Select Mode", options)
        
        if idx == 0:
            return "quick"
        elif idx == 1:
            return "fulldev"
        return None
    
    def _select_mode_cli(self):
        """CLI numbered mode selection."""
        print("\\n" + "="*60)
        print(f"{self.__class__.__name__.upper()}")
        print("="*60)
        print(f"Environment: {self.env.upper()}")
        print("\\n[1] ⚡ Quick Mode")
        print("    Fast analysis with smart defaults")
        print("\\n[2] 🔧 FullDev Mode")
        print("    Detailed configuration and options")
        print("\\n[0] Cancel")
        
        try:
            choice = input("\\nSelect [0-2]: ").strip()
            if choice == "1":
                return "quick"
            elif choice == "2":
                return "fulldev"
        except (KeyboardInterrupt, EOFError):
            pass
        return None
    
    # =========================================================================
    # TARGET SELECTION (Mode-dependent)
    # =========================================================================
    
    def _select_targets(self):
        """Select target(s) based on current mode."""
        if self.mode == "quick":
            return self._select_targets_quick()
        else:
            return self._select_targets_fulldev()
    
    def _select_targets_quick(self):
        """Quick mode: numbered list of recent + favorites."""
        history = self._load_history()
        options = []
        path_map = {}
        
        # Build numbered options
        counter = 1
        
        # Recent paths (last 5)
        for path in history.get("recent_paths", [])[:5]:
            if os.path.exists(path):
                options.append(f"[{counter}] 📁 {self._shorten(path)}")
                path_map[str(counter)] = path
                counter += 1
        
        # Favorites
        for name, path in history.get("favorites", {}).items():
            if os.path.exists(path):
                options.append(f"[{counter}] ⭐ {name}: {self._shorten(path)}")
                path_map[str(counter)] = path
                counter += 1
        
        # Custom input option
        options.append(f"[{counter}] ➕ Enter custom path...")
        custom_key = str(counter)
        
        # Show selection
        if self.env == "kodi":
            idx = self.config.dialog_select("Select Target", options)
            selected_key = str(idx + 1) if idx >= 0 else None
        else:
            print("\\nSelect target:")
            for opt in options:
                print(f"  {opt}")
            selected_key = input("\\nSelect: ").strip()
        
        # Handle selection
        if selected_key == custom_key:
            return self._get_custom_path()
        
        selected_path = path_map.get(selected_key)
        if selected_path:
            self._add_to_history(selected_path)
            return [selected_path]
        
        return []
    
    def _select_targets_fulldev(self):
        """FullDev mode: multi-select with configuration."""
        if self.env == "dev":
            # CLI: multiple paths
            print("\\nFullDev Mode - Enter paths (empty to finish):")
            paths = []
            while True:
                path = input(f"  Path {len(paths)+1}: ").strip()
                if not path:
                    break
                if os.path.exists(path):
                    paths.append(path)
                    self._add_to_history(path)
                else:
                    print(f"    ⚠️  Not found: {path}")
            return paths
        else:
            # Kodi: simplified (can extend later)
            return self._select_targets_quick()
    
    def _get_custom_path(self):
        """Get custom path from user."""
        if self.env == "kodi":
            path = self.config.dialog_input("Enter full path", "")
        else:
            path = input("Enter full path: ").strip()
        
        if path and os.path.exists(path):
            self._add_to_history(path)
            return [path]
        
        self._notify("Path not found", "ERROR")
        return []
    
    # =========================================================================
    # CORE PROCESSING (Override this in each module)
    # =========================================================================
    
    def _process_target(self, target_path, options=None):
        """
        Process a single target.
        
        OVERRIDE THIS METHOD in each module.
        
        Args:
            target_path: Path to process
            options: Optional dict of processing options (FullDev mode)
        
        Returns:
            dict with results
        """
        # Example structure - replace with actual logic
        result = {
            "target": target_path,
            "status": "success",  # or "error", "warning"
            "timestamp": datetime.now().isoformat(),
            "data": {},  # Module-specific results
            "message": "Processing complete"
        }
        
        # TODO: Implement actual processing logic here
        # This is where each module does its unique work
        
        return result
    
    # =========================================================================
    # OUTPUT & REPORTING (Universal)
    # =========================================================================
    
    def _show_results(self):
        """Display results in environment-appropriate way."""
        # Generate summary
        total = len(self.results)
        success = sum(1 for r in self.results.values() if r.get("status") == "success")
        errors = total - success
        
        # Save report
        report_path = self._save_report()
        
        # Show summary
        summary = f"Processed: {total}\\nSuccess: {success}\\nErrors: {errors}"
        
        if self.env == "kodi":
            if errors == 0:
                self.config.dialog_ok("Complete", f"✅ {summary}\\n\\nReport: {report_path}")
            else:
                self.config.dialog_ok("Complete", f"⚠️ {summary}\\n\\nReport: {report_path}")
        else:
            print("\\n" + "="*60)
            print("RESULTS")
            print("="*60)
            print(summary)
            for target, result in self.results.items():
                icon = "✅" if result["status"] == "success" else "❌"
                print(f"{icon} {self._shorten(target)}")
            print(f"\\nReport: {report_path}")
    
    def _save_report(self):
        """Save report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.__class__.__name__.lower()}_{timestamp}.txt"
        
        if self.env == "kodi":
            report_dir = os.path.join(self.config.profile_path, "reports")
        else:
            report_dir = os.path.expanduser("~/fluiddev_reports")
        
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, filename)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("="*70 + "\\n")
            f.write(f"{self.__class__.__name__.upper()} REPORT\\n")
            f.write("="*70 + "\\n")
            f.write(f"Mode: {self.mode}\\n")
            f.write(f"Environment: {self.env}\\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\\n\\n")
            
            for target, result in self.results.items():
                f.write(f"\\nTarget: {target}\\n")
                f.write("-" * 70 + "\\n")
                f.write(json.dumps(result, indent=2, default=str))
                f.write("\\n")
        
        return report_path
    
    # =========================================================================
    # HISTORY & UTILITIES
    # =========================================================================
    
    def _load_history(self):
        """Load recent paths and favorites."""
        if self.env == "kodi":
            history_file = os.path.join(self.config.profile_path, f"{self.__class__.__name__.lower()}_history.json")
        else:
            history_file = os.path.expanduser(f"~/.fluiddev/{self.__class__.__name__.lower()}_history.json")
        
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    return json.load(f)
            except:
                pass
        
        return {"recent_paths": [], "favorites": {}}
    
    def _add_to_history(self, path):
        """Add path to recent history."""
        history = self._load_history()
        
        if path in history["recent_paths"]:
            history["recent_paths"].remove(path)
        
        history["recent_paths"].insert(0, path)
        history["recent_paths"] = history["recent_paths"][:10]
        
        # Save
        if self.env == "kodi":
            history_file = os.path.join(self.config.profile_path, f"{self.__class__.__name__.lower()}_history.json")
        else:
            history_file = os.path.expanduser(f"~/.fluiddev/{self.__class__.__name__.lower()}_history.json")
            os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
    
    def _shorten(self, path, max_len=40):
        """Shorten path for display."""
        if len(path) <= max_len:
            return path
        return "..." + path[-(max_len-3):]
    
    def _notify(self, message, icon="INFO"):
        """Show notification."""
        if self.env == "kodi":
            self.config.notification(self.__class__.__name__, message, icon)
        else:
            prefix = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}.get(icon, "ℹ️")
            print(f"{prefix} {message}")


# =========================================================================
# STANDALONE ENTRY POINT (for personal use)
# =========================================================================

if __name__ == "__main__":
    # Minimal config for standalone usage
    class StandaloneConfig:
        def __init__(self):
            self.profile_path = os.path.expanduser("~/.fluiddev")
            os.makedirs(self.profile_path, exist_ok=True)
        
        def dialog_select(self, heading, options):
            print(f"\\n{heading}")
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
            print(f"\\n[{icon}] {title}: {message}")
    
    # Run module
    config = StandaloneConfig()
    module = {ModuleName}(config)
    module.run()
'''