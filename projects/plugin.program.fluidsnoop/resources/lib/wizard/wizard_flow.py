import uuid

class WizardSession:
    """Manages wizard state across steps"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.session_id = None
        self.data = {
            'research_type': None,
            'targets': [],  # List of addon IDs
            'modules': [],
            'formats': [],
            'options': {}
        }
        self.step = 1
        self.max_steps = 5
        
    def start_new(self):
        """Initialize new wizard session"""
        self.session_id = str(uuid.uuid4())[:8]
        self.data = {
            'research_type': None,
            'targets': [],
            'modules': [],
            'formats': [],
            'options': {}
        }
        self.step = 1
        return self.session_id
    
    def set_research_type(self, research_type):
        """Set research type and auto-configure if applicable"""
        from wizard.research_types import (
            get_research_type, 
            get_auto_selected_modules,
            requires_comparison
        )
        
        self.data['research_type'] = research_type
        research = get_research_type(research_type)
        
        if research and research.get('auto_select'):
            enabled = self.config.get_enabled_modules()
            auto_modules = get_auto_selected_modules(research_type, enabled)
            self.data['modules'] = auto_modules
            
            # Also set default formats from research type
            if research.get('formats'):
                self.data['formats'] = research['formats']
        
        # If requires comparison, ensure we know that
        if requires_comparison(research_type):
            self.data['needs_comparison'] = True
    
    def add_target(self, addon_id):
        """Add target addon"""
        if addon_id not in self.data['targets']:
            self.data['targets'].append(addon_id)
    
    def remove_target(self, addon_id):
        """Remove target addon"""
        if addon_id in self.data['targets']:
            self.data['targets'].remove(addon_id)
    
    def set_modules(self, modules):
        """Set selected modules"""
        self.data['modules'] = modules
    
    def toggle_module(self, module):
        """Toggle module selection"""
        if module in self.data['modules']:
            self.data['modules'].remove(module)
        else:
            self.data['modules'].append(module)
    
    def set_formats(self, formats):
        """Set output formats"""
        self.data['formats'] = formats
    
    def toggle_format(self, fmt):
        """Toggle format selection"""
        if fmt in self.data['formats']:
            self.data['formats'].remove(fmt)
        else:
            self.data['formats'].append(fmt)
    
    def set_option(self, key, value):
        """Set custom option"""
        self.data['options'][key] = value
    
    def next_step(self):
        """Advance to next step"""
        if self.step < self.max_steps:
            self.step += 1
        return self.step
    
    def prev_step(self):
        """Go back to previous step"""
        if self.step > 1:
            self.step -= 1
        return self.step
    
    def get_step_data(self):
        """Get current step configuration"""
        steps = {
            1: {'name': 'research_type', 'title': 31101},
            2: {'name': 'target_addon', 'title': 31102},
            3: {'name': 'modules', 'title': 31103},
            4: {'name': 'formats', 'title': 31104},
            5: {'name': 'confirm', 'title': 31105}
        }
        return steps.get(self.step)
    
    def validate_step(self):
        """Validate current step data"""
        if self.step == 1:
            return self.data['research_type'] is not None
        elif self.step == 2:
            return len(self.data['targets']) > 0
        elif self.step == 3:
            return len(self.data['modules']) > 0
        elif self.step == 4:
            return len(self.data['formats']) > 0
        elif self.step == 5:
            return self._validate_all()
        return False
    
    def _validate_all(self):
        """Validate complete configuration"""
        from wizard.research_types import requires_comparison
        
        if not self.data['research_type']:
            return False
        if not self.data['targets']:
            return False
        if not self.data['modules']:
            return False
        if not self.data['formats']:
            return False
        
        # Check comparison requirement
        if requires_comparison(self.data['research_type']):
            if len(self.data['targets']) < 2:
                return False
        
        return True
    
    def get_advice(self):
        """Get contextual advice for current configuration"""
        from wizard.research_types import get_research_type
        
        advice = []
        
        # Research type specific advice
        if self.data['research_type']:
            research = get_research_type(self.data['research_type'])
            if research and research.get('advice'):
                advice.append({
                    'type': 'info',
                    'message': research['advice']
                })
        
        # Module combination advice
        if 'network' in self.data['modules'] and 'ui' not in self.data['modules']:
            if self.data['research_type'] in ['download_flow', 'network_study']:
                advice.append({
                    'type': 'suggestion',
                    'message': 'Add UI Intercept to capture progress dialogs?',
                    'action': 'add_module:ui'
                })
        
        # Comparison advice
        if self.data.get('needs_comparison') and len(self.data['targets']) < 2:
            advice.append({
                'type': 'requirement',
                'message': 'This research type requires 2 addons for comparison',
                'action': 'add_target'
            })
        
        # Code injection warning
        if 'inject' in self.data['modules']:
            if not self.data['options'].get('inject_confirmed'):
                advice.append({
                    'type': 'warning',
                    'message': 'Code injection requires manual file editing. Instructions will be provided.',
                    'action': 'confirm_inject'
                })
        
        return advice
    
    def finalize(self):
        """Create database session and return configuration"""
        if not self._validate_all():
            return None
        
        # Create session in database
        self.db.create_session(
            session_id=self.session_id,
            research_type=self.data['research_type'],
            target_addon=','.join(self.data['targets']),
            modules=self.data['modules'],
            formats=self.data['formats']
        )
        
        return {
            'session_id': self.session_id,
            'research_type': self.data['research_type'],
            'targets': self.data['targets'],
            'modules': self.data['modules'],
            'formats': self.data['formats'],
            'options': self.data['options']
        }


class WizardAdvisor:
    """Provides intelligent suggestions during wizard"""
    
    def __init__(self, config):
        self.config = config
    
    def suggest_research_type(self, goal_description):
        """Suggest research type based on user goal"""
        goal_lower = goal_description.lower()
        
        keywords = {
            'favorites': 'favorites_extraction',
            'bookmark': 'favorites_extraction',
            'download': 'download_flow',
            'save file': 'download_flow',
            'menu': 'menu_structure',
            'navigation': 'menu_structure',
            'dialog': 'ui_audit',
            'notification': 'ui_audit',
            'message': 'ui_audit',
            'network': 'network_study',
            'api': 'network_study',
            'url': 'network_study',
            'database': 'db_reverse',
            'sqlite': 'db_reverse',
            'compare': 'addon_compare',
            'difference': 'addon_compare',
            'debug': 'hook_debug',
            'fix': 'hook_debug',
            'broken': 'hook_debug'
        }
        
        for keyword, research_type in keywords.items():
            if keyword in goal_lower:
                return research_type
        
        return 'custom'
    
    def suggest_modules_for_addon(self, addon_id):
        """Analyze addon type and suggest modules"""
        suggestions = []
        
        if 'video' in addon_id:
            suggestions = ['runtime', 'ui', 'network']
        elif 'program' in addon_id:
            suggestions = ['runtime', 'ui', 'fs']
        elif 'service' in addon_id:
            suggestions = ['runtime', 'db', 'network']
        else:
            suggestions = ['runtime', 'ui']
        
        return suggestions