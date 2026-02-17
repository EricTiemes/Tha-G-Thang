import xbmcgui
import xbmcplugin
import xbmc

class Router:
    """Routes requests to appropriate handlers"""
    
    def __init__(self, config):
        self.config = config
        self.db = None
        self.modules = {}
        self._init_database()
        
    def _init_database(self):
        """Initialize database connection"""
        from persistence.database import Database
        self.db = Database(self.config)
    
    def _get_module(self, name):
        """Lazy load modules"""
        if name not in self.modules:
            if name == 'ui':
                from modules.ui_intercept import UIIntercept
                self.modules['ui'] = UIIntercept(self.config)
            elif name == 'db':
                from modules.db_spy import DBSpy
                self.modules['db'] = DBSpy(self.config)
            elif name == 'network':
                from modules.net_monitor import NetMonitor
                self.modules['network'] = NetMonitor(self.config)
            elif name == 'runtime':
                from modules.runtime_hook import RuntimeHook
                self.modules['runtime'] = RuntimeHook(self.config)
            elif name == 'fs':
                from modules.fs_monitor import FSMonitor
                self.modules['fs'] = FSMonitor(self.config)
            elif name == 'inject':
                from modules.code_inject import CodeInject
                self.modules['inject'] = CodeInject(self.config)
            elif name == 'export':
                from modules.export_handler import ExportHandler
                self.modules['export'] = ExportHandler(self.config)
            elif name == 'pattern':
                from modules.pattern_extract import PatternExtract
                self.modules['pattern'] = PatternExtract(self.config)
        return self.modules.get(name)
    
    def route(self, handle, params):
        """Route request based on mode"""
        mode = params.get('mode', 'main')
        
        if mode == 'main':
            self._main_menu(handle)
        elif mode == 'wizard':
            self._wizard(handle, params)
        elif mode == 'resume_session':
            self._resume_session(handle)
        elif mode == 'recent_sessions':
            self._recent_sessions(handle)
        elif mode == 'view_session':
            self._view_session(handle, params)
        elif mode == 'compare_sessions':
            self._compare_menu(handle)
        elif mode == 'do_compare':
            self._do_comparison(handle, params)
        elif mode == 'start_monitoring':
            self._start_monitoring(params)
        elif mode == 'stop_monitoring':
            self._stop_monitoring()
        elif mode == 'export_session':
            self._export_session(params)
        elif mode == 'delete_session':
            self._delete_session(params)
        elif mode == 'inject_code':
            self._inject_code(params)
        elif mode == 'settings':
            self._open_settings()
        else:
            self._main_menu(handle)
    
    def _main_menu(self, handle):
        """Build main menu"""
        xbmcplugin.setPluginCategory(handle, 'FluidSnoop')
        
        active = self.db.get_active_session()
        items = []
        
        items.append({
            'label': self.config.get_localized(31001),
            'url': self._build_url({'mode': 'wizard', 'step': '1'}),
            'icon': 'DefaultAddonProgram.png',
            'isFolder': True
        })
        
        if active:
            items.append({
                'label': f"[ACTIVE] {active['id']}: {active.get('research_type', 'unknown')}",
                'url': self._build_url({'mode': 'resume_session'}),
                'icon': 'DefaultAddonService.png',
                'isFolder': True
            })
        
        items.append({
            'label': self.config.get_localized(31003),
            'url': self._build_url({'mode': 'recent_sessions'}),
            'icon': 'DefaultAddonWebViewer.png',
            'isFolder': True
        })
        
        items.append({
            'label': self.config.get_localized(31004),
            'url': self._build_url({'mode': 'compare_sessions'}),
            'icon': 'DefaultAddonService.png',
            'isFolder': True
        })
        
        items.append({
            'label': self.config.get_localized(31006),
            'url': self._build_url({'mode': 'settings'}),
            'icon': 'DefaultAddonService.png',
            'isFolder': False
        })
        
        self._add_items(handle, items)
        xbmcplugin.endOfDirectory(handle)
    
    def _wizard(self, handle, params):
        """Handle wizard steps"""
        from wizard.research_types import RESEARCH_TYPES
        
        step = int(params.get('step', 1))
        
        if step == 1:
            items = []
            for research_id, research in RESEARCH_TYPES.items():
                label = research_id.replace('_', ' ').title()
                item = {
                    'label': label,
                    'url': self._build_url({
                        'mode': 'wizard',
                        'step': '2',
                        'research_type': research_id
                    }),
                    'icon': research.get('icon', 'DefaultAddon.png'),
                    'isFolder': True
                }
                items.append(item)
            
            self._add_items(handle, items)
            xbmcplugin.endOfDirectory(handle)
    
    def _start_monitoring(self, params):
        """Start monitoring"""
        session_id = params.get('session_id', 'test')
        modules = params.get('modules', 'ui,db').split(',')
        target = params.get('target')
        
        for mod_name in modules:
            if mod_name:
                module = self._get_module(mod_name)
                if module:
                    module.start(session_id=session_id, target_filter=target)
        
        xbmcgui.Dialog().notification(
            'FluidSnoop',
            'Monitoring started',
            xbmcgui.NOTIFICATION_INFO
        )
    
    def _stop_monitoring(self):
        """Stop all monitoring"""
        for mod_name, module in self.modules.items():
            if hasattr(module, 'stop'):
                module.stop()
        
        active = self.db.get_active_session()
        if active:
            self.db.update_session(active['id'], status='completed')
        
        xbmcgui.Dialog().notification(
            'FluidSnoop',
            'Monitoring stopped',
            xbmcgui.NOTIFICATION_INFO
        )
    
    def _recent_sessions(self, handle):
        """Show recent sessions"""
        sessions = self.db.get_recent_sessions(20)
        
        items = []
        for session in sessions:
            label = f"{session['id']}: {session.get('research_type', 'unknown')}"
            item = {
                'label': label,
                'url': self._build_url({
                    'mode': 'view_session',
                    'session_id': session['id']
                }),
                'icon': 'DefaultAddonWebViewer.png',
                'isFolder': True
            }
            items.append(item)
        
        self._add_items(handle, items)
        xbmcplugin.endOfDirectory(handle)
    
    def _view_session(self, handle, params):
        """View session details"""
        session_id = params.get('session_id')
        
        items = []
        items.append({
            'label': 'Export Results',
            'url': self._build_url({
                'mode': 'export_session',
                'session_id': session_id
            }),
            'icon': 'DefaultFile.png',
            'isFolder': False
        })
        
        items.append({
            'label': 'Delete Session',
            'url': self._build_url({
                'mode': 'delete_session',
                'session_id': session_id
            }),
            'icon': 'DefaultIconError.png',
            'isFolder': False
        })
        
        self._add_items(handle, items)
        xbmcplugin.endOfDirectory(handle)
    
    def _export_session(self, params):
        """Export session"""
        session_id = params.get('session_id')
        exporter = self._get_module('export')
        
        if exporter:
            results = exporter.export_session(session_id, self.db, ['json'])
            xbmcgui.Dialog().ok('Export', 'Export completed')
    
    def _delete_session(self, params):
        """Delete session"""
        session_id = params.get('session_id')
        if xbmcgui.Dialog().yesno('Confirm', 'Delete this session?'):
            self.db.delete_session(session_id)
    
    def _compare_menu(self, handle):
        """Show comparison menu"""
        sessions = self.db.get_recent_sessions(20)
        
        items = []
        for session in sessions:
            label = f"Select: {session['id']}"
            item = {
                'label': label,
                'url': self._build_url({
                    'mode': 'do_compare',
                    'session_1': session['id']
                }),
                'icon': 'DefaultAddon.png',
                'isFolder': True
            }
            items.append(item)
        
        self._add_items(handle, items)
        xbmcplugin.endOfDirectory(handle)
    
    def _do_comparison(self, handle, params):
        """Perform comparison"""
        xbmcgui.Dialog().ok('Compare', 'Comparison feature')
    
    def _inject_code(self, params):
        """Generate code injection"""
        xbmcgui.Dialog().ok('Inject', 'Code injection feature')
    
    def _open_settings(self):
        """Open addon settings"""
        xbmc.executebuiltin('Addon.OpenSettings(plugin.program.fluidsnoop)')
    
    def _resume_session(self, handle):
        """Resume active session"""
        active = self.db.get_active_session()
        if active:
            items = []
            items.append({
                'label': 'Stop Monitoring',
                'url': self._build_url({'mode': 'stop_monitoring'}),
                'icon': 'DefaultIconError.png',
                'isFolder': False
            })
            self._add_items(handle, items)
            xbmcplugin.endOfDirectory(handle)
        else:
            xbmcgui.Dialog().ok('No Active Session', 'No monitoring session is active')
    
    def _build_url(self, params):
        """Build plugin URL"""
        from urllib.parse import urlencode
        base = f"plugin://{self.config.addon_id}/"
        if params:
            return f"{base}?{urlencode(params)}"
        return base
    
    def _add_items(self, handle, items):
        """Add items to directory"""
        for item in items:
            li = xbmcgui.ListItem(item['label'])
            li.setArt({'icon': item.get('icon', 'DefaultAddon.png')})
            xbmcplugin.addDirectoryItem(
                handle,
                item['url'],
                li,
                item.get('isFolder', False)
            )