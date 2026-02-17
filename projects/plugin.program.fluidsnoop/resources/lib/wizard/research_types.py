RESEARCH_TYPES = {
    'favorites_extraction': {
        'name': 31200,  # Copy Favorites System
        'description': 'Extract add/remove/show favorites implementation',
        'icon': 'DefaultAddonFavourites.png',
        'modules': ['db', 'ui'],
        'auto_select': True,
        'advice': 'Captures database operations and user feedback for favorites',
        'formats': ['json', 'ai_handoff']
    },
    'download_flow': {
        'name': 31201,  # Debug Download Flow
        'description': 'Trace URL to file to notification sequence',
        'icon': 'DefaultAddonRepository.png',
        'modules': ['network', 'fs', 'ui'],
        'auto_select': True,
        'advice': 'Tracks network requests, file operations, and progress dialogs',
        'formats': ['compact', 'detailed']
    },
    'hook_debug': {
        'name': 31202,  # Fix Broken Hook
        'description': 'Compare old vs new addon behavior',
        'icon': 'DefaultAddonService.png',
        'modules': ['runtime', 'ui'],
        'auto_select': False,
        'advice': 'Requires two addons for comparison. Optional: Code injection for precise debugging',
        'formats': ['detailed', 'ai_handoff'],
        'requires_comparison': True
    },
    'menu_structure': {
        'name': 31203,  # Extract Menu Structure
        'description': 'Map navigation flow and menu items',
        'icon': 'DefaultAddonProgram.png',
        'modules': ['runtime', 'ui'],
        'auto_select': True,
        'advice': 'Captures directory item additions and user navigation',
        'formats': ['json', 'compact']
    },
    'ui_audit': {
        'name': 31204,  # Audit UI Messages
        'description': 'Find all user-facing text and dialogs',
        'icon': 'DefaultAddonInfoProvider.png',
        'modules': ['ui'],
        'auto_select': True,
        'advice': 'Lightweight capture of all notifications and dialogs',
        'formats': ['compact']
    },
    'network_study': {
        'name': 31205,  # Study Network Patterns
        'description': 'API endpoint discovery and request analysis',
        'icon': 'DefaultAddonWebViewer.png',
        'modules': ['network', 'pattern'],
        'auto_select': True,
        'advice': 'Tracks HTTP requests and extracts URL patterns',
        'formats': ['json', 'ai_handoff']
    },
    'db_reverse': {
        'name': 31206,  # Reverse DB Schema
        'description': 'Table structure and query extraction',
        'icon': 'DefaultAddonDatabase.png',
        'modules': ['db'],
        'auto_select': True,
        'advice': 'Monitors all database operations to reconstruct schema',
        'formats': ['detailed']
    },
    'addon_compare': {
        'name': 31207,  # Compare Addons
        'description': 'Side-by-side behavior analysis',
        'icon': 'DefaultAddonService.png',
        'modules': ['runtime', 'db', 'ui'],
        'auto_select': False,
        'advice': 'Select two addons to compare. Same research type recommended.',
        'formats': ['detailed', 'ai_handoff'],
        'requires_comparison': True,
        'multi_addon': True
    },
    'custom': {
        'name': 31208,  # Custom Research
        'description': 'User-configurable monitoring',
        'icon': 'DefaultAddon.png',
        'modules': [],  # User selects all
        'auto_select': False,
        'advice': 'Select modules and configure manually',
        'formats': ['json', 'ai_handoff', 'compact', 'detailed']
    }
}

MODULE_INFO = {
    'ui': {
        'name': 31300,
        'description': 31301,
        'icon': 'DefaultAddonInfoProvider.png'
    },
    'db': {
        'name': 31302,
        'description': 31303,
        'icon': 'DefaultAddonDatabase.png'
    },
    'network': {
        'name': 31304,
        'description': 31305,
        'icon': 'DefaultAddonWebViewer.png'
    },
    'runtime': {
        'name': 31306,
        'description': 31307,
        'icon': 'DefaultAddonService.png'
    },
    'fs': {
        'name': 31308,
        'description': 31309,
        'icon': 'DefaultAddonRepository.png'
    },
    'inject': {
        'name': 31310,
        'description': 31311,
        'icon': 'DefaultAddonProgram.png'
    }
}

FORMAT_INFO = {
    'json': {
        'name': 'JSON (Raw Data)',
        'description': 'Machine-readable complete data',
        'extension': 'json'
    },
    'ai_handoff': {
        'name': 'AI Handoff (Markdown)',
        'description': 'Context-rich report for LLM processing',
        'extension': 'md'
    },
    'compact': {
        'name': 'Compact (Summary)',
        'description': 'One-line summaries for quick review',
        'extension': 'txt'
    },
    'detailed': {
        'name': 'Detailed (Full Report)',
        'description': 'Complete event details with code',
        'extension': 'txt'
    }
}

def get_research_type(research_id):
    """Get research type configuration"""
    return RESEARCH_TYPES.get(research_id)

def get_module_info(module_id):
    """Get module information"""
    return MODULE_INFO.get(module_id)

def get_auto_selected_modules(research_id, enabled_modules):
    """Get auto-selected modules for research type, filtered by enabled"""
    research = RESEARCH_TYPES.get(research_id)
    if not research:
        return []
    
    auto_modules = research.get('modules', [])
    return [m for m in auto_modules if m in enabled_modules]

def requires_comparison(research_id):
    """Check if research type requires multiple addons"""
    research = RESEARCH_TYPES.get(research_id)
    if research:
        return research.get('requires_comparison', False)
    return False

def allows_multiple_addons(research_id):
    """Check if research type supports multiple addons"""
    research = RESEARCH_TYPES.get(research_id)
    if research:
        return research.get('multi_addon', False)
    return False