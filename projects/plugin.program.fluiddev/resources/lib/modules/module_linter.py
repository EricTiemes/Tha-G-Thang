import os
import json
import subprocess
from datetime import datetime


class Linter:
    """Universal linter with Quick and FullDev modes."""
    
    def __init__(self, config):
        self.config = config
        self.env = self._detect_environment()
        self.mode = None  # 'quick' or 'fulldev'
        self.results = {}
        
    def _detect_environment(self):
        """Detect if running in Kodi or Dev environment."""
        try:
            import xbmc  # noqa: F401
            return "kodi"
        except ImportError:
            return "dev"
    
    def run_interactive(self):
        """Main interactive entry point."""
        # Select mode
        self.mode = self._select_mode()
        
        # Select target(s)
        targets = self._select_targets()
        
        if not targets:
            self._notify("No targets selected", "WARNING")
            return
        
        # Run linting
        self._notify(f"Linting {len(targets)} target(s)...", "INFO")
        
        for target in targets:
            self.results[target] = self._lint_target(target)
        
        # Show results
        self._show_results()
    
    def _select_mode(self):
        """Ask user: Quick or FullDev mode."""
        if self.env == "kodi":
            # Kodi GUI dialog
            options = ["⚡ Quick Lint (fast, presets)", "🔧 FullDev (detailed config)"]
            idx = self.config.dialog_select("Select Mode", options)
            return "quick" if idx == 0 else "fulldev" if idx == 1 else None
        else:
            # CLI numbered menu
            print("\\n" + "="*50)
            print("FLUIDDEV LINTER")
            print("="*50)
            print("Environment:", self.env.upper())
            print("\\n[1] ⚡ Quick Lint")
            print("    Fast analysis with presets")
            print("\\n[2] 🔧 FullDev Mode")
            print("    Detailed configuration")
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
    
    def _select_targets(self):
        """Select target paths to lint."""
        if self.mode == "quick":
            return self._quick_target_select()
        else:
            return self._fulldev_target_select()
    
    def _quick_target_select(self):
        """Quick mode: numbered list of recent + favorites."""
        history = self._load_history()
        
        # Build options
        options = []
        path_map = {}
        
        # Recent paths
        if history.get("recent_paths"):
            for i, path in enumerate(history["recent_paths"][:5], 1):
                if os.path.exists(path):
                    options.append(f"[{i}] 📁 {self._shorten_path(path)}")
                    path_map[str(i)] = path
        
        # Favorites
        if history.get("favorites"):
            for name, path in history["favorites"].items():
                if os.path.exists(path):
                    key = str(len(path_map) + 1)
                    options.append(f"[{key}] ⭐ {name}: {self._shorten_path(path)}")
                    path_map[key] = path
        
        # Custom option
        custom_key = str(len(path_map) + 1)
        options.append(f"[{custom_key}] ➕ Enter custom path...")
        
        if self.env == "kodi":
            idx = self.config.dialog_select("Select Target", options)
            if idx < 0:
                return []
            selected_key = str(idx + 1)
        else:
            print("\\nSelect target:")
            for opt in options:
                print(f"  {opt}")
            selected_key = input("\\nSelect: ").strip()
        
        if selected_key == custom_key:
            # Custom path input
            if self.env == "kodi":
                custom_path = self.config.dialog_input("Enter path", "")
            else:
                custom_path = input("Enter full path: ").strip()
            
            if custom_path and os.path.exists(custom_path):
                self._add_to_history(custom_path)
                return [custom_path]
            return []
        
        selected_path = path_map.get(selected_key)
        if selected_path:
            self._add_to_history(selected_path)
            return [selected_path]
        
        return []
    
    def _fulldev_target_select(self):
        """FullDev mode: multi-select with configuration."""
        if self.env == "dev":
            # CLI: allow multiple paths
            print("\\nFullDev Mode - Select targets")
            print("Enter paths (one per line, empty line to finish):")
            paths = []
            while True:
                path = input(f"  Path {len(paths)+1}: ").strip()
                if not path:
                    break
                if os.path.exists(path):
                    paths.append(path)
                    self._add_to_history(path)
                else:
                    print(f"    ⚠️  Path not found: {path}")
            return paths
        else:
            # Kodi: simplified for now
            return self._quick_target_select()
    
    def _lint_target(self, target_path):
        """Run linter on single target."""
        # Detect project type
        project_type = self._detect_project_type(target_path)
        
        # Get linter config
        linter_config = self._get_linter_config(project_type)
        
        # Run appropriate linter
        if linter_config.get("command") == "ruff":
            return self._run_ruff(target_path, linter_config)
        else:
            return {"status": "error", "message": "Unknown linter"}
    
    def _detect_project_type(self, path):
        """Auto-detect project type."""
        # Check for addon.xml (Kodi addon)
        if os.path.exists(os.path.join(path, "addon.xml")):
            return "kodi_addon"
        
        # Check for package.json (Node.js)
        if os.path.exists(os.path.join(path, "package.json")):
            return "nodejs"
        
        # Check for requirements.txt or setup.py (Python)
        if any(os.path.exists(os.path.join(path, f)) for f in ["requirements.txt", "setup.py", "pyproject.toml"]):
            return "python_package"
        
        # Default: generic python
        return "python"
    
    def _get_linter_config(self, project_type):
        """Get linter configuration for project type."""
        configs = {
            "kodi_addon": {
                "command": "ruff",
                "args": ["check", "--line-length", "120"],
                "extensions": [".py", ".xml"]
            },
            "python_package": {
                "command": "ruff", 
                "args": ["check", "--line-length", "88"],
                "extensions": [".py"]
            },
            "nodejs": {
                "command": "eslint",
                "args": ["--format", "compact"],
                "extensions": [".js", ".ts"]
            },
            "python": {
                "command": "ruff",
                "args": ["check"],
                "extensions": [".py"]
            }
        }
        return configs.get(project_type, configs["python"])
    
    def _run_ruff(self, target_path, config):
        """Run Ruff linter."""
        cmd = [config["command"]] + config["args"] + [target_path]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                "status": "success" if result.returncode == 0 else "issues_found",
                "command": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "issues_count": len([line for line in result.stdout.split("\\n") if line.strip()])
            }
        except FileNotFoundError:
            return {
                "status": "error",
                "message": "Ruff not installed. Run: pip install ruff"
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "error", 
                "message": "Linting timeout (60s)"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _show_results(self):
        """Display linting results."""
        total_issues = sum(
            r.get("issues_count", 0) 
            for r in self.results.values() 
            if r.get("status") == "issues_found"
        )
        
        # Generate report
        report_path = self._save_report()
        
        # Show summary
        if self.env == "kodi":
            if total_issues == 0:
                self.config.dialog_ok("Lint Complete", "✅ No issues found!")
            else:
                self.config.dialog_ok(
                    "Lint Complete", 
                    f"⚠️  {total_issues} issues found\\n\\nReport saved to:\\n{report_path}"
                )
        else:
            print("\\n" + "="*50)
            print("LINT COMPLETE")
            print("="*50)
            for target, result in self.results.items():
                status = result.get("status", "unknown")
                issues = result.get("issues_count", 0)
                icon = "✅" if status == "success" else "⚠️" if status == "issues_found" else "❌"
                print(f"{icon} {self._shorten_path(target)}: {issues} issues")
            print(f"\\nReport: {report_path}")
    
    def _save_report(self):
        """Save linting report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"lint_report_{timestamp}.txt"
        
        if self.env == "kodi":
            report_dir = os.path.join(self.config.profile_path, "reports")
        else:
            report_dir = os.path.expanduser("~/lint_reports")
        
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, filename)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("="*70 + "\\n")
            f.write("FLUIDDEV LINT REPORT\\n")
            f.write("="*70 + "\\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\\n")
            f.write(f"Mode: {self.mode}\\n")
            f.write(f"Environment: {self.env}\\n\\n")
            
            for target, result in self.results.items():
                f.write(f"\\nTarget: {target}\\n")
                f.write("-" * 70 + "\\n")
                f.write(f"Status: {result.get('status', 'unknown')}\\n")
                
                if result.get("stdout"):
                    f.write("\\nOutput:\\n")
                    f.write(result["stdout"])
                
                if result.get("stderr"):
                    f.write("\\nErrors:\\n")
                    f.write(result["stderr"])
                
                f.write("\\n")
        
        return report_path
    
    def _load_history(self):
        """Load recent paths and favorites."""
        if self.env == "kodi":
            history_file = os.path.join(self.config.profile_path, "linter_history.json")
        else:
            history_file = os.path.expanduser("~/.fluiddev/linter_history.json")
        
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {"recent_paths": [], "favorites": {}}
    
    def _add_to_history(self, path):
        """Add path to recent history."""
        history = self._load_history()
        
        # Remove if exists (move to top)
        if path in history["recent_paths"]:
            history["recent_paths"].remove(path)
        
        # Add to front
        history["recent_paths"].insert(0, path)
        
        # Keep only last 10
        history["recent_paths"] = history["recent_paths"][:10]
        
        # Save
        if self.env == "kodi":
            history_file = os.path.join(self.config.profile_path, "linter_history.json")
        else:
            history_file = os.path.expanduser("~/.fluiddev/linter_history.json")
            os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
    
    def _shorten_path(self, path, max_len=40):
        """Shorten path for display."""
        if len(path) <= max_len:
            return path
        return "..." + path[-(max_len-3):]
    
    def _notify(self, message, icon="INFO"):
        """Show notification (Kodi) or print (Dev)."""
        if self.env == "kodi":
            self.config.notification("FluidDev Linter", message, icon)
        else:
            prefix = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}.get(icon, "ℹ️")
            print(f"{prefix} {message}")


# Standalone entry point (for personal use)
if __name__ == "__main__":
    # Create minimal config for standalone mode
    class StandaloneConfig:
        """Minimal config for standalone usage."""
        
        def __init__(self):
            self.profile_path = os.path.expanduser("~/.fluiddev")
            os.makedirs(self.profile_path, exist_ok=True)
        
        def dialog_select(self, heading, options):
            print(f"\\n{heading}")
            for i, opt in enumerate(options):
                print(f"  [{i}] {opt}")
            try:
                return int(input("Select: "))
            except Exception:
                return -1
        
        def dialog_input(self, heading, default=""):
            print(f"{heading}: ", end="")
            result = input()
            return result if result else default
        
        def notification(self, title, message, icon="INFO"):
            print(f"\\n[{icon}] {title}: {message}")
    
    # Run linter
    config = StandaloneConfig()
    linter = Linter(config)
    linter.run_interactive()