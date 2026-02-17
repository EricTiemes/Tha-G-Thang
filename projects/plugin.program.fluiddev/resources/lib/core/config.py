import os

# Import environment classes
try:
    from resources.lib.core.environment import KodiEnvironment, DevEnvironment
    ENV_AVAILABLE = True
except ImportError:
    ENV_AVAILABLE = False


class Config:
    """Central configuration and environment manager."""
    
    def __init__(self):
        self.env = self._detect_environment()
        self._discovered_modules = None
        self._template_registry = None
        
        # Ensure paths exist
        os.makedirs(self.reports_path, exist_ok=True)
        os.makedirs(self.cache_path, exist_ok=True)
    
    def _detect_environment(self):
        """Detect and initialize appropriate environment."""
        if not ENV_AVAILABLE:
            return self._create_fallback_env()
        
        try:
            import xbmc  # noqa: F401
            return KodiEnvironment()
        except ImportError:
            return DevEnvironment()
    
    def _create_fallback_env(self):
        """Create minimal fallback environment."""
        class FallbackEnv:
            name = "fallback"
            def log(self, msg, level=1): print(f"[FALLBACK] {msg}")
            def translate_path(self, p): return p
            def vfs_exists(self, p): return os.path.exists(p)
            def vfs_listdir(self, p):
                if not os.path.exists(p):
                    return ([], [])  # Return tuple, not list
                items = os.listdir(p)
                dirs = [i for i in items if os.path.isdir(os.path.join(p, i))]
                files = [i for i in items if os.path.isfile(os.path.join(p, i))]
                return (dirs, files)  # Return tuple matching xbmcvfs format
            def notification(self, t, m, **k): print(f"[NOTE] {t}: {m}")
            def dialog_ok(self, h, m): input(f"{h}: {m}")
            def dialog_select(self, h, o): return 0
            def dialog_input(self, h, d=""): return input(f"{h}: ") or d
            def get_addon_info(self, i): return ""
            def get_setting(self, s, d=""): return d
            def set_setting(self, s, v): pass
            def open_settings(self): pass
        return FallbackEnv()
    
    @property
    def addon_id(self):
        return self.env.get_addon_info("id")
    
    @property
    def addon_path(self):
        return self.env.get_addon_info("path")
    
    @property
    def profile_path(self):
        return self.env.get_addon_info("profile")
    
    @property
    def addons_path(self):
        return self.env.translate_path("special://home/addons")
    
    @property
    def reports_path(self):
        path = os.path.join(self.profile_path, "reports")
        os.makedirs(path, exist_ok=True)
        return path
    
    @property
    def cache_path(self):
        path = os.path.join(self.profile_path, "cache")
        os.makedirs(path, exist_ok=True)
        return path
    
    @property
    def templates_path(self):
        return os.path.join(self.addon_path, "resources", "templates")
    
    @property
    def modules_path(self):
        return os.path.join(self.addon_path, "resources", "lib", "modules")
    
    @property
    def is_kodi(self):
        return self.env.name == "kodi"
    
    @property
    def is_dev(self):
        return self.env.name == "dev"
    
    def get_setting(self, setting_id, default=""):
        return self.env.get_setting(setting_id, default)
    
    def get_bool(self, setting_id, default=False):
        val = self.get_setting(setting_id, str(default).lower())
        return val.lower() in ("true", "1", "yes", "on")
    
    def get_int(self, setting_id, default=0):
        try:
            return int(self.get_setting(setting_id, str(default)))
        except ValueError:
            return default
    
    def set_setting(self, setting_id, value):
        return self.env.set_setting(setting_id, value)
    
    def log(self, message, level=1):
        self.env.log(message, level)
    
    def notification(self, title, message, icon="INFO", time=3000):
        self.env.notification(title, message, icon, time)
    
    def dialog_ok(self, heading, message):
        self.env.dialog_ok(heading, message)
    
    def dialog_select(self, heading, options):
        return self.env.dialog_select(heading, options)
    
    def dialog_input(self, heading, default=""):
        return self.env.dialog_input(heading, default)
    
    def open_settings(self):
        self.env.open_settings()
    
    def vfs_exists(self, path):
        return self.env.vfs_exists(path)
    
    def vfs_listdir(self, path):
        return self.env.vfs_listdir(path)
    
    def discover_modules(self, force_refresh=False):
        """Auto-discover available modules from filesystem."""
        if self._discovered_modules is not None and not force_refresh:
            return self._discovered_modules
        
        modules = []
        modules_dir = self.modules_path
        
        if not os.path.exists(modules_dir):
            self.log(f"Modules directory not found: {modules_dir}", 3)
            return modules
        
        for filename in os.listdir(modules_dir):
            if filename.startswith("module_") and filename.endswith(".py"):
                module_id = filename[7:-3]
                settings_file = os.path.join(
                    self.addon_path, "resources", "settings", f"{module_id}.json"
                )
                has_settings = os.path.exists(settings_file)
                enabled = self.get_bool(f"module_{module_id}_enabled", True)
                
                modules.append({
                    "id": module_id,
                    "filename": filename,
                    "name": module_id.replace("_", " ").title(),
                    "class_name": self._snake_to_class(module_id),
                    "enabled": enabled,
                    "has_settings": has_settings,
                    "settings_file": settings_file if has_settings else None
                })
        
        modules.sort(key=lambda x: x["name"])
        self._discovered_modules = modules
        return modules
    
    def get_enabled_modules(self):
        """Get only enabled modules."""
        return [m for m in self.discover_modules() if m["enabled"]]
    
    def get_module_class(self, module_id):
        """Dynamically import and return module class."""
        try:
            module_path = f"resources.lib.modules.module_{module_id}"
            class_name = self._snake_to_class(module_id)
            module = __import__(module_path, fromlist=[class_name])
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            self.log(f"Failed to load module {module_id}: {e}", 3)
            return None
    
    def _snake_to_class(self, snake_str):
        """Convert snake_case to ClassName."""
        parts = snake_str.split("_")
        return "".join(p.title() for p in parts)
    
    def get_template_registry(self):
        """Get unified template registry."""
        if self._template_registry is not None:
            return self._template_registry
        
        registry = {
            "pattern": {
                "icon": "🔬",
                "name": "Pattern Extraction",
                "description": "Extract code patterns using AST analysis",
                "templates": {
                    "quick": {
                        "id": "pattern_quick",
                        "name": "Quick Pattern Find",
                        "filters": {"pattern_type": "name", "max_results": 20},
                        "delivery": "ai_handoff"
                    },
                    "full": {
                        "id": "pattern_full",
                        "name": "Deep Pattern Analysis",
                        "filters": {"pattern_types": ["name", "api", "decorator"]},
                        "delivery": "detailed_report"
                    },
                    "custom": {
                        "id": "pattern_custom",
                        "name": "Custom Pattern Search",
                        "user_fields": ["pattern_type", "search_pattern", "case_sensitive"],
                        "delivery": "ai_handoff"
                    }
                }
            },
            "hooks": {
                "icon": "🕸️",
                "name": "Hook Tracing",
                "description": "Trace execution flows and identify hooks",
                "templates": {
                    "quick": {
                        "id": "hooks_quick",
                        "name": "Quick Hook Finder",
                        "filters": {"find_entry_points": True, "find_framework_hooks": True},
                        "delivery": "ai_handoff"
                    },
                    "full": {
                        "id": "hooks_full",
                        "name": "Complete Flow Analysis",
                        "filters": {"build_call_graph": True, "find_unreachable": True},
                        "delivery": "detailed_report"
                    },
                    "custom": {
                        "id": "hooks_custom",
                        "name": "Custom Flow Analysis",
                        "user_fields": ["start_function", "trace_depth", "find_hooks"],
                        "delivery": "detailed_report"
                    }
                }
            },
            "clean": {
                "icon": "🧹",
                "name": "Code Cleaning",
                "description": "Remove addon-specific clutter",
                "templates": {
                    "quick": {
                        "id": "clean_quick",
                        "name": "Quick Clean",
                        "operations": ["replace_addon_id", "replace_addon_name"],
                        "delivery": "code_bundle"
                    },
                    "full": {
                        "id": "clean_full",
                        "name": "Deep Refactoring",
                        "operations": ["replace_addon_id", "generalize_vars", "clean_comments"],
                        "delivery": "blueprint"
                    },
                    "custom": {
                        "id": "clean_custom",
                        "name": "Custom Cleaning",
                        "user_fields": ["replace_addon_id", "clean_paths", "custom_replacements"],
                        "delivery": "code_bundle"
                    }
                }
            },
            "bundle": {
                "icon": "📦",
                "name": "Code Bundling",
                "description": "Package code for reuse",
                "templates": {
                    "quick": {
                        "id": "bundle_quick",
                        "name": "Quick Bundle",
                        "bundle_type": "simple",
                        "delivery": "code_bundle"
                    },
                    "full": {
                        "id": "bundle_full",
                        "name": "Complete Package",
                        "bundle_type": "complete",
                        "delivery": "complete_package"
                    }
                }
            },
            "structure": {
                "icon": "🏗️",
                "name": "Structure Analysis",
                "description": "Analyze addon architecture",
                "templates": {
                    "quick": {
                        "id": "structure_quick",
                        "name": "Quick Structure Check",
                        "delivery": "ai_handoff"
                    },
                    "full": {
                        "id": "structure_full",
                        "name": "Deep Architecture Analysis",
                        "delivery": "detailed_report"
                    }
                }
            },
            "deps": {
                "icon": "🔗",
                "name": "Dependency Analysis",
                "description": "Analyze dependencies and imports",
                "templates": {
                    "quick": {
                        "id": "deps_quick",
                        "name": "Quick Dependency Check",
                        "delivery": "ai_handoff"
                    },
                    "full": {
                        "id": "deps_full",
                        "name": "Complete Dependency Audit",
                        "delivery": "detailed_report"
                    }
                }
            },
            "compare": {
                "icon": "⚖️",
                "name": "Comparison",
                "description": "Compare two addons",
                "templates": {
                    "structure": {"id": "compare_structure", "name": "Compare Structures"},
                    "routing": {"id": "compare_routing", "name": "Compare Routing"},
                    "deps": {"id": "compare_deps", "name": "Compare Dependencies"},
                    "patterns": {"id": "compare_patterns", "name": "Compare Patterns"}
                }
            },
            "usecase": {
                "icon": "🎯",
                "name": "Use Cases",
                "description": "Specific pattern extraction",
                "templates": {
                    "download": {"id": "usecase_download", "name": "Download Flow", "pattern": "download.*"},
                    "ui": {"id": "usecase_ui", "name": "UI Dialogs", "pattern": "xbmcgui.Dialog"},
                    "cache": {"id": "usecase_cache", "name": "Caching Patterns", "pattern": "cache.*"},
                    "settings": {"id": "usecase_settings", "name": "Settings Handler", "pattern": "getSetting"}
                }
            }
        }
        
        self._template_registry = registry
        return registry
    
    def get_template(self, category, template_type="quick"):
        """Get specific template from registry."""
        registry = self.get_template_registry()
        cat = registry.get(category, {})
        templates = cat.get("templates", {})
        return templates.get(template_type)
    
    def list_template_categories(self):
        """List all template categories."""
        registry = self.get_template_registry()
        return [(k, v["name"], v["icon"]) for k, v in registry.items()]
