"""
FluidDev - Main Menu Dashboard
Dynamic dashboard based on enabled modules and templates.
"""

try:
    import xbmcplugin
    import xbmcgui
    KODI_GUI = True
except ImportError:
    KODI_GUI = False

from resources.lib.core.config import Config


class MainMenu:
    """Dynamic main menu for FluidDev."""
    
    def __init__(self):
        self.config = Config()
        self.handle = 0
        
    def show(self, addon_handle=0):
        """Display dynamic main menu."""
        self.handle = addon_handle
        if KODI_GUI:
            xbmcplugin.setContent(self.handle, 'videos')
        
        self._build_quick_section()
        self._build_module_sections()
        self._build_tools_section()
        self._build_admin_section()
        
        if KODI_GUI:
            xbmcplugin.endOfDirectory(self.handle)
    
    def _add_item(self, title, action, description="", is_folder=True, icon=""):
        """Add menu item."""
        if not KODI_GUI:
            print(f"  [{icon}] {title}")
            return
        
        addon_id = self.config.addon_id
        url = f"plugin://{addon_id}/?action={action}"
        li = xbmcgui.ListItem(f"{icon} {title}" if icon else title)
        li.setInfo('video', {'title': title, 'plot': description})
        li.setProperty('IsPlayable', 'false')
        xbmcplugin.addDirectoryItem(handle=self.handle, url=url, listitem=li, isFolder=is_folder)
    
    def _add_separator(self, title):
        """Add visual separator."""
        if KODI_GUI:
            li = xbmcgui.ListItem(f"[COLOR gray]{title}[/COLOR]")
            li.setProperty('IsPlayable', 'false')
            xbmcplugin.addDirectoryItem(handle=self.handle, url="", listitem=li, isFolder=False)
        else:
            print(f"\n{title}")
    
    def _build_quick_section(self):
        """Build quick actions section."""
        self._add_separator("⚡ Quick Actions")
        self._add_item("Health Check", "quick_health", "Quick scan of selected addon", icon="🔍")
        self._add_item("Template Wizard", "template_wizard", "Guided template selection", icon="🧙")
        self._add_item("Recent Templates", "recent_templates", "Recently used templates", icon="📜")
    
    def _build_module_sections(self):
        """Build sections for each enabled module."""
        modules = self.config.get_enabled_modules()
        for module in modules:
            self._add_separator(f"{module['name']}")
            category = module['id'].replace('_', '')
            templates = self.config.get_template_registry().get(category, {}).get('templates', {})
            
            if 'quick' in templates:
                self._add_item(f"Quick {module['name']}", f"run_template|{category}|quick", f"Fast {module['name'].lower()} analysis", icon="⚡")
            if 'full' in templates:
                self._add_item(f"Deep {module['name']}", f"run_template|{category}|full", f"Comprehensive {module['name'].lower()} analysis", icon="🔬")
            if 'custom' in templates:
                self._add_item(f"Custom {module['name']}", f"run_template|{category}|custom", f"User-defined {module['name'].lower()} parameters", icon="🎛️")
            
            self._add_item(f"Browse {module['name']} Templates", f"browse_templates|{category}", f"View all {module['name'].lower()} templates", icon="📋")
    
    def _build_tools_section(self):
        """Build tools section."""
        self._add_separator("🛠️ Tools")
        self._add_item("Compare Addons", "compare_addons", "Side-by-side addon comparison", icon="⚖️")
        self._add_item("Global Scan", "global_scan", "Scan all installed addons", icon="🌐")
        if self.config.is_dev:
            self._add_item("Dev Console", "dev_console", "Development tools", icon="💻")
    
    def _build_admin_section(self):
        """Build admin section."""
        self._add_separator("⚙️ Administration")
        self._add_item("Module Manager", "module_manager", "Enable/disable modules", icon="📦")
        self._add_item("Settings", "open_settings", "Configure addon", icon="🔧")
        if self.config.is_dev:
            self._add_item("Environment Info", "env_info", f"Current: {self.config.env.name}", icon="ℹ️")
    
    def execute_action(self, action, handle=0, params=None):
        """Execute menu action."""
        self.handle = handle
        params = params or {}
        parts = action.split('|')
        base_action = parts[0]
        
        handlers = {
            'quick_health': self._do_health_check,
            'template_wizard': self._run_template_wizard,
            'recent_templates': self._show_recent_templates,
            'run_template': lambda: self._run_template(parts[1], parts[2]) if len(parts) >= 3 else None,
            'browse_templates': lambda: self._browse_templates(parts[1]) if len(parts) >= 2 else None,
            'compare_addons': self._do_compare,
            'global_scan': self._do_global_scan,
            'module_manager': self._open_module_manager,
            'open_settings': self._open_settings,
            'dev_console': self._open_dev_console,
            'env_info': self._show_env_info,
        }
        
        handler = handlers.get(base_action)
        if handler:
            try:
                handler()
            except Exception as e:
                self.config.log(f"Action error: {e}", 3)
                self.config.notification("Error", str(e), "ERROR")
        else:
            self.config.notification("FluidDev", f"Unknown action: {base_action}")
    
    def _do_health_check(self):
        """Quick health check."""
        from resources.lib.core.addon_scanner import AddonScanner
        scanner = AddonScanner(self.config)
        addons = scanner.get_installed_addons()
        if not addons:
            self.config.dialog_ok("FluidDev", "No addons found")
            return
        names = [a['name'] for a in addons]
        idx = self.config.dialog_select("Select addon", names)
        if idx >= 0:
            addon = addons[idx]
            self.config.notification("FluidDev", f"Analyzing {addon['name']}...")
            self.config.dialog_ok("Health Check", f"Analysis complete for {addon['name']}")
    
    def _run_template_wizard(self):
        """Launch template wizard."""
        categories = self.config.list_template_categories()
        options = [f"{icon} {name}" for _, name, icon in categories]
        idx = self.config.dialog_select("Select Category", options)
        if idx >= 0:
            cat_key = categories[idx][0]
            self._browse_templates(cat_key)
    
    def _show_recent_templates(self):
        """Show recently used templates."""
        self.config.dialog_ok("Recent Templates", "Feature coming in v1.2")
    
    def _run_template(self, category, template_type):
        """Run specific template."""
        template = self.config.get_template(category, template_type)
        if template:
            self.config.notification("FluidDev", f"Running {template['name']}...")
            self.config.dialog_ok("Template", f"Would run: {template['name']}")
        else:
            self.config.notification("Error", "Template not found", "ERROR")
    
    def _browse_templates(self, category):
        """Browse templates in category."""
        registry = self.config.get_template_registry()
        cat = registry.get(category, {})
        templates = cat.get('templates', {})
        options = [f"{t['name']}" for t in templates.values()]
        idx = self.config.dialog_select(cat.get('name', 'Templates'), options)
        if idx >= 0:
            template_type = list(templates.keys())[idx]
            self._run_template(category, template_type)
    
    def _do_compare(self):
        """Compare two addons."""
        self.config.dialog_ok("Compare", "Select first addon...")
    
    def _do_global_scan(self):
        """Global scan all addons."""
        if self.config.dialog_select("Confirm", ["Cancel", "Scan All Addons"]) == 1:
            self.config.notification("FluidDev", "Scanning...")
    
    def _open_module_manager(self):
        """Open module manager."""
        modules = self.config.discover_modules()
        options = []
        for m in modules:
            status = "✓" if m['enabled'] else "✗"
            options.append(f"{status} {m['name']}")
        idx = self.config.dialog_select("Toggle Modules (select to toggle)", options)
        if idx >= 0:
            module = modules[idx]
            new_state = not module['enabled']
            self.config.set_setting(f"module_{module['id']}_enabled", str(new_state).lower())
            self.config.notification("FluidDev", f"{module['name']} {'enabled' if new_state else 'disabled'}")
    
    def _open_settings(self):
        """Open addon settings."""
        self.config.open_settings()
    
    def _open_dev_console(self):
        """Open dev console."""
        if not self.config.is_dev:
            return
        print("\n" + "="*50)
        print("FLUIDDEV DEV CONSOLE")
        print("="*50)
        print(f"Environment: {self.config.env.name}")
        print(f"Addon path: {self.config.addon_path}")
        print(f"Profile path: {self.config.profile_path}")
        print(f"Modules found: {len(self.config.discover_modules())}")
        print("="*50)
        input("\nPress Enter to continue...")
    
    def _show_env_info(self):
        """Show environment info."""
        info = f"""
Environment: {self.config.env.name}
Addon ID: {self.config.addon_id}
Version: {self.config.get_addon_info('version')}
Modules: {len(self.config.get_enabled_modules())} enabled
        """.strip()
        self.config.dialog_ok("Environment Info", info)