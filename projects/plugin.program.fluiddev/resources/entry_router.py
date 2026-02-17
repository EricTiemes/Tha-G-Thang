"""
FluidDev - Entry Router
Blind router - parses argv and delegates only.
"""
from urllib.parse import parse_qs


class EntryRouter:
    """Routes entry point calls to appropriate handlers."""
    
    def route(self, argv):
        """Route based on argv parameters."""
        addon_handle = self._parse_handle(argv)
        params = self._parse_params(argv)
        action = params.get('action', [None])[0]
        self._delegate(action, addon_handle, params)
    
    def _parse_handle(self, argv):
        """Parse addon handle from argv[1]."""
        if len(argv) > 1:
            try:
                return int(argv[1])
            except ValueError:
                pass
        return 0
    
    def _parse_params(self, argv):
        """Parse URL parameters from argv[2]."""
        if len(argv) <= 2 or not argv[2]:
            return {}
        param_string = argv[2]
        if param_string.startswith('?'):
            param_string = param_string[1:]
        return parse_qs(param_string)
    
    def _delegate(self, action, handle, params):
        """Delegate to appropriate handler."""
        from resources.lib.display.main_menu import MainMenu
        menu = MainMenu()
        if action:
            menu.execute_action(action, handle, params)
        else:
            menu.show(handle)
