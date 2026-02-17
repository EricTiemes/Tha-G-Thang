'''"""
FluidDev - Code Cleaner Module
Removes addon-specific clutter and generalizes code for reuse.
"""
import os
import re
import ast
import xbmcvfs


class CodeCleaner:
    """Cleans and generalizes addon code for reuse."""
    
    def __init__(self, config):
        self.config = config
        self.addon_id_pattern = None
        self.addon_name_pattern = None
        
    def clean_addon_code(self, addon_path, code_snippet, addon_info=None):
        """Clean a code snippet by removing addon-specific identifiers."""
        if not addon_info:
            addon_info = self._get_addon_info(addon_path)
        
        cleaned = code_snippet
        
        # Step 1: Replace addon ID
        if addon_info.get('id'):
            cleaned = self._replace_addon_id(cleaned, addon_info['id'])
        
        # Step 2: Replace addon name
        if addon_info.get('name'):
            cleaned = self._replace_addon_name(cleaned, addon_info['name'])
        
        # Step 3: Replace hardcoded paths
        cleaned = self._replace_hardcoded_paths(cleaned)
        
        # Step 4: Replace specific variable names with generic ones
        cleaned = self._generalize_variables(cleaned)
        
        # Step 5: Remove addon-specific comments
        cleaned = self._clean_comments(cleaned)
        
        # Step 6: Normalize formatting
        cleaned = self._normalize_formatting(cleaned)
        
        return {
            'original': code_snippet,
            'cleaned': cleaned,
            'changes_made': self._count_changes(code_snippet, cleaned),
            'addon_info': addon_info
        }
    
    def create_reusable_module(self, addon_path, extracted_functions, module_name="reusable_module"):
        """Create a reusable Python module from extracted functions."""
        results = {
            'module_name': module_name,
            'imports': [],
            'functions': [],
            'classes': [],
            'output_file': None
        }
        
        addon_info = self._get_addon_info(addon_path)
        all_imports = set()
        
        # Collect all imports from source files
        for func in extracted_functions:
            file_imports = self._extract_file_imports(addon_path, func['file'])
            all_imports.update(file_imports)
        
        # Clean imports
        results['imports'] = self._clean_imports(list(all_imports))
        
        # Clean each function
        for func in extracted_functions:
            cleaned = self.clean_addon_code(addon_path, func['code'], addon_info)
            results['functions'].append({
                'name': func['name'],
                'original_file': func['file'],
                'cleaned_code': cleaned['cleaned']
            })
        
        # Generate module content
        module_content = self._generate_module_content(results, module_name)
        results['module_content'] = module_content
        
        # Save to file
        output_path = os.path.join(self.config.reports_path, f"{module_name}.py")
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(module_content)
            results['output_file'] = output_path
        except Exception as e:
            self.config.log(f"Error saving module: {e}")
        
        return results
    
    def generalize_for_blueprint(self, addon_path, pattern_type):
        """Create a blueprint template from addon patterns."""
        results = {
            'pattern_type': pattern_type,
            'blueprint': {},
            'placeholders': []
        }
        
        addon_info = self._get_addon_info(addon_path)
        
        if pattern_type == 'video_plugin':
            results['blueprint'] = self._create_video_plugin_blueprint(addon_path, addon_info)
        elif pattern_type == 'service':
            results['blueprint'] = self._create_service_blueprint(addon_path, addon_info)
        elif pattern_type == 'script':
            results['blueprint'] = self._create_script_blueprint(addon_path, addon_info)
        else:
            results['blueprint'] = self._create_generic_blueprint(addon_path, addon_info)
        
        # Identify placeholders
        results['placeholders'] = self._extract_placeholders(results['blueprint'])
        
        return results
    
    def _get_addon_info(self, addon_path):
        """Extract addon info from addon.xml."""
        info = {'id': '', 'name': '', 'version': '', 'provider': ''}
        
        xml_file = os.path.join(addon_path, 'addon.xml')
        if not os.path.exists(xml_file):
            return info
        
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            info['id'] = root.get('id', '')
            info['name'] = root.get('name', '')
            info['version'] = root.get('version', '')
            info['provider'] = root.get('provider-name', '')
        except Exception as e:
            self.config.log(f"Error parsing addon.xml: {e}")
        
        return info
    
    def _replace_addon_id(self, code, addon_id):
        """Replace addon-specific IDs with placeholders."""
        # Common patterns
        patterns = [
            (rf'["\']{re.escape(addon_id)}["\']', '"YOUR_ADDON_ID"'),
            (rf'xbmcaddon\.Addon\(["\']{re.escape(addon_id)}["\']\)', 'xbmcaddon.Addon()'),
            (rf'xbmcaddon\.Addon\(["\']{re.escape(addon_id)}["\']\)', 'xbmcaddon.Addon()'),
        ]
        
        cleaned = code
        for pattern, replacement in patterns:
            cleaned = re.sub(pattern, replacement, cleaned)
        
        # Replace ID variations (e.g., plugin.video.xyz -> YOUR_ADDON_ID)
        id_variants = [
            addon_id,
            addon_id.replace('.', '_'),
            addon_id.replace('.', ''),
            addon_id.replace('.', '-')
        ]
        
        for variant in id_variants:
            if variant and variant != addon_id:
                cleaned = re.sub(rf'\b{re.escape(variant)}\b', 'YOUR_ADDON_ID', cleaned)
        
        return cleaned
    
    def _replace_addon_name(self, code, addon_name):
        """Replace addon name with placeholder."""
        if not addon_name:
            return code
        
        # Replace in strings
        patterns = [
            (rf'["\']{re.escape(addon_name)}["\']', '"YOUR_ADDON_NAME"'),
        ]
        
        cleaned = code
        for pattern, replacement in patterns:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _replace_hardcoded_paths(self, code):
        """Replace hardcoded paths with configurable ones."""
        patterns = [
            # Android paths
            (r'/storage/emulated/0/[^\s\'"\]]+', 'YOUR_BASE_PATH'),
            (r'/sdcard/[^\s\'"\]]+', 'YOUR_BASE_PATH'),
            # Kodi special paths
            (r'special://[^\s\'"\]]+', 'YOUR_SPECIAL_PATH'),
            # Common hardcoded paths
            (r'["\']/[\w/]+/addons/[^\s\'"\]]+', '"YOUR_ADDON_PATH"'),
        ]
        
        cleaned = code
        for pattern, replacement in patterns:
            cleaned = re.sub(pattern, replacement, cleaned)
        
        return cleaned
    
    def _generalize_variables(self, code):
        """Replace specific variable names with generic ones."""
        # Common patterns to generalize
        generalizations = [
            # Addon-specific prefixes
            (r'\b(\w+)_addon\b', r'\1_addon', 'addon'),
            (r'\b(\w+)_plugin\b', r'\1_plugin', 'plugin'),
            (r'\b(\w+)_script\b', r'\1_script', 'script'),
            # Specific naming patterns
            (r'\bmy_(\w+)\b', r'my_\1', 'the_\1'),
            (r'\bthis_(\w+)\b', r'this_\1', 'current_\1'),
        ]
        
        cleaned = code
        # This is a simplified version - full implementation would use AST
        
        return cleaned
    
    def _clean_comments(self, code):
        """Remove addon-specific comments but keep structure hints."""
        lines = code.split('\\n')
        cleaned_lines = []
        
        for line in lines:
            # Keep TODO/FIXME/NOTE comments
            if re.search(r'#\\s*(TODO|FIXME|NOTE|HACK|XXX)', line, re.IGNORECASE):
                cleaned_lines.append(line)
            # Remove author/copyright comments
            elif re.search(r'#\\s*(author|copyright|license|@author|@copyright)', line, re.IGNORECASE):
                continue
            # Remove empty comments
            elif re.match(r'\\s*#\\s*$', line):
                continue
            else:
                cleaned_lines.append(line)
        
        return '\\n'.join(cleaned_lines)
    
    def _normalize_formatting(self, code):
        """Normalize code formatting."""
        # Remove trailing whitespace
        lines = [line.rstrip() for line in code.split('\\n')]
        
        # Remove multiple blank lines
        cleaned_lines = []
        prev_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            cleaned_lines.append(line)
            prev_blank = is_blank
        
        return '\\n'.join(cleaned_lines)
    
    def _count_changes(self, original, cleaned):
        """Count the number of changes made."""
        orig_lines = original.split('\\n')
        clean_lines = cleaned.split('\\n')
        
        changes = 0
        for i, (orig, clean) in enumerate(zip(orig_lines, clean_lines)):
            if orig != clean:
                changes += 1
        
        return {
            'lines_changed': changes,
            'total_lines': len(orig_lines)
        }
    
    def _extract_file_imports(self, addon_path, file_path):
        """Extract imports from a specific file."""
        imports = set()
        full_path = os.path.join(addon_path, file_path)
        
        if not os.path.exists(full_path):
            return imports
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(f"import {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ''
                        names = ', '.join([a.name for a in node.names])
                        imports.add(f"from {module} import {names}")
        except Exception:
            pass
        
        return imports
    
    def _clean_imports(self, imports):
        """Remove duplicate and addon-specific imports."""
        # Remove local imports (they won't work in new context)
        cleaned = []
        for imp in imports:
            if 'resources.lib' in imp or 'from .' in imp:
                continue
            cleaned.append(imp)
        
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for imp in cleaned:
            if imp not in seen:
                seen.add(imp)
                unique.append(imp)
        
        return unique
    
    def _generate_module_content(self, results, module_name):
        """Generate the final module content."""
        lines = []
        
        # Header
        lines.append(f'"""')
        lines.append(f'Reusable module generated by FluidDev')
        lines.append(f'Original addon: {results["addon_info"]["name"]}')
        lines.append(f'"""')
        lines.append('')
        
        # Imports
        if results['imports']:
            lines.extend(results['imports'])
            lines.append('')
        
        # Functions
        for func in results['functions']:
            lines.append(f'# Originally from: {func["original_file"]}')
            lines.append(func['cleaned_code'])
            lines.append('')
        
        return '\\n'.join(lines)
    
    def _create_video_plugin_blueprint(self, addon_path, addon_info):
        """Create blueprint for video plugin."""
        return {
            'type': 'video_plugin',
            'entry_point': 'default.py',
            'required_structure': ['resources/lib'],
            'key_components': {
                'router': 'URL routing setup',
                'list_builder': 'Directory item builder',
                'resolver': 'Video URL resolver',
                'settings': 'Addon settings handler'
            },
            'template_variables': {
                'ADDON_ID': addon_info.get('id', 'YOUR_ADDON_ID'),
                'ADDON_NAME': addon_info.get('name', 'YOUR_ADDON_NAME')
            }
        }
    
    def _create_service_blueprint(self, addon_path, addon_info):
        """Create blueprint for service addon."""
        return {
            'type': 'service',
            'entry_point': 'service.py',
            'required_structure': [],
            'key_components': {
                'monitor': 'XBMC Monitor class',
                'background_task': 'Background processing',
                'settings_watcher': 'Settings change handler'
            },
            'template_variables': {
                'ADDON_ID': addon_info.get('id', 'YOUR_ADDON_ID'),
                'ADDON_NAME': addon_info.get('name', 'YOUR_ADDON_NAME')
            }
        }
    
    def _create_script_blueprint(self, addon_path, addon_info):
        """Create blueprint for script addon."""
        return {
            'type': 'script',
            'entry_point': 'default.py',
            'required_structure': ['resources/lib'],
            'key_components': {
                'main_dialog': 'Main UI dialog',
                'action_handler': 'User action handler',
                'utils': 'Utility functions'
            },
            'template_variables': {
                'ADDON_ID': addon_info.get('id', 'YOUR_ADDON_ID'),
                'ADDON_NAME': addon_info.get('name', 'YOUR_ADDON_NAME')
            }
        }
    
    def _create_generic_blueprint(self, addon_path, addon_info):
        """Create generic blueprint."""
        return {
            'type': 'generic',
            'entry_point': 'default.py',
            'required_structure': [],
            'key_components': {
                'main': 'Main entry point',
                'utils': 'Utility functions'
            },
            'template_variables': {
                'ADDON_ID': addon_info.get('id', 'YOUR_ADDON_ID'),
                'ADDON_NAME': addon_info.get('name', 'YOUR_ADDON_NAME')
            }
        }
    
    def _extract_placeholders(self, blueprint):
        """Extract placeholder variables from blueprint."""
        placeholders = []
        
        if 'template_variables' in blueprint:
            for key, value in blueprint['template_variables'].items():
                if 'YOUR_' in str(value):
                    placeholders.append({
                        'name': key,
                        'placeholder': value,
                        'description': f'Replace with your {key.lower()}'
                    })
        
        return placeholders
    
    def generate_report(self, addon, clean_results):
        """Generate cleaning report."""
        report = f"[B]Code Cleaning: {addon['name']}[/B]\\n\\n"
        
        if 'changes_made' in clean_results:
            changes = clean_results['changes_made']
            report += f"[B]Changes Made:[/B]\\n"
            report += f"  Lines changed: {changes['lines_changed']}/{changes['total_lines']}\\n"
            report += f"  Percentage: {int(changes['lines_changed']/changes['total_lines']*100)}%\\n\\n"
        
        if 'module_content' in clean_results:
            report += "[B]Generated Module Preview:[/B]\\n"
            lines = clean_results['module_content'].split('\\n')[:20]
            for line in lines:
                report += f"  {line}\\n"
            if len(clean_results['module_content'].split('\\n')) > 20:
                report += "  ...\\n"
        
        if 'output_file' in clean_results and clean_results['output_file']:
            report += f"\\n[B]Saved to:[/B] {clean_results['output_file']}\\n"
        
        if 'placeholders' in clean_results and clean_results['placeholders']:
            report += f"\\n[B]Placeholders to Fill:[/B]\\n"
            for ph in clean_results['placeholders']:
                report += f"  • {ph['name']}: {ph['description']}\\n"
        
        return report
'''

print("module_code_cleaner.py created")
