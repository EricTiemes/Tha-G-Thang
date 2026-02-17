'''"""
FluidDev - Code Bundler Module
Packages extracted code into reusable bundles and blueprints.
"""
import os
import json
import zipfile
from datetime import datetime
import xbmcvfs


class CodeBundler:
    """Bundles extracted code into reusable packages."""
    
    def __init__(self, config):
        self.config = config
        self.bundle_index = []
        
    def create_bundle(self, addon_path, extracted_items, bundle_name=None):
        """Create a reusable code bundle from extracted items."""
        if not bundle_name:
            bundle_name = f"bundle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        results = {
            'bundle_name': bundle_name,
            'created': datetime.now().isoformat(),
            'source_addon': None,
            'items': [],
            'files_created': [],
            'bundle_path': None
        }
        
        # Get addon info
        addon_info = self._get_addon_info(addon_path)
        results['source_addon'] = addon_info
        
        # Process each extracted item
        for item in extracted_items:
            bundled_item = {
                'name': item.get('name', 'unknown'),
                'type': item.get('type', 'function'),
                'original_file': item.get('file', ''),
                'original_code': item.get('code', ''),
                'metadata': {
                    'line': item.get('line', 0),
                    'args': item.get('args', []),
                    'decorator': item.get('decorator', None)
                }
            }
            results['items'].append(bundled_item)
        
        # Create bundle directory
        bundle_dir = os.path.join(self.config.cache_path, 'bundles', bundle_name)
        os.makedirs(bundle_dir, exist_ok=True)
        
        # Generate bundle files
        self._generate_bundle_files(bundle_dir, results)
        results['bundle_path'] = bundle_dir
        
        # Save bundle index
        self._update_bundle_index(results)
        
        return results
    
    def create_blueprint_template(self, addon_path, pattern_type, template_name=None):
        """Create a blueprint template from addon patterns."""
        if not template_name:
            template_name = f"blueprint_{pattern_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        results = {
            'template_name': template_name,
            'pattern_type': pattern_type,
            'created': datetime.now().isoformat(),
            'source_addon': None,
            'structure': {},
            'files': [],
            'placeholders': [],
            'template_path': None
        }
        
        addon_info = self._get_addon_info(addon_path)
        results['source_addon'] = addon_info
        
        # Analyze structure
        results['structure'] = self._analyze_structure(addon_path, pattern_type)
        
        # Generate template files
        template_dir = os.path.join(self.config.templates_path, template_name)
        os.makedirs(template_dir, exist_ok=True)
        
        self._generate_template_files(template_dir, results)
        results['template_path'] = template_dir
        
        return results
    
    def export_to_acode(self, bundle_path, export_name=None):
        """Export bundle to Acode-friendly format (Android)."""
        if not export_name:
            export_name = f"fluiddev_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        results = {
            'export_name': export_name,
            'format': 'acode',
            'files': [],
            'android_path': None
        }
        
        # Android Downloads path
        android_downloads = '/storage/emulated/0/Download'
        if not os.path.exists(android_downloads):
            android_downloads = '/sdcard/Download'
        
        export_dir = os.path.join(android_downloads, 'FluidDevExports', export_name)
        os.makedirs(export_dir, exist_ok=True)
        
        # Copy bundle files
        if os.path.isdir(bundle_path):
            for item in os.listdir(bundle_path):
                src = os.path.join(bundle_path, item)
                dst = os.path.join(export_dir, item)
                
                if os.path.isfile(src):
                    import shutil
                    shutil.copy2(src, dst)
                    results['files'].append(dst)
        
        results['android_path'] = export_dir
        return results
    
    def generate_ai_handoff(self, addon, analysis_results, handoff_type='pattern_extraction'):
        """Generate AI-style handoff summary."""
        handoff = {
            'type': handoff_type,
            'addon': {
                'id': addon.get('id'),
                'name': addon.get('name'),
                'version': addon.get('version')
            },
            'summary': '',
            'key_findings': [],
            'recommendations': [],
            'code_snippets': []
        }
        
        if handoff_type == 'pattern_extraction':
            handoff['summary'] = self._generate_pattern_summary(addon, analysis_results)
            handoff['key_findings'] = self._extract_key_findings(analysis_results)
            handoff['code_snippets'] = self._extract_snippets(analysis_results)
        
        elif handoff_type == 'hook_analysis':
            handoff['summary'] = self._generate_hook_summary(addon, analysis_results)
            handoff['key_findings'] = self._extract_hook_findings(analysis_results)
        
        elif handoff_type == 'cleaned_code':
            handoff['summary'] = self._generate_cleaning_summary(addon, analysis_results)
            handoff['recommendations'] = self._generate_recommendations(analysis_results)
        
        # Generate formatted text
        handoff['formatted'] = self._format_handoff(handoff)
        
        # Save handoff
        handoff_path = os.path.join(
            self.config.reports_path, 
            f"handoff_{addon['id']}_{datetime.now().strftime('%H%M%S')}.md"
        )
        try:
            with open(handoff_path, 'w', encoding='utf-8') as f:
                f.write(handoff['formatted'])
            handoff['file_path'] = handoff_path
        except Exception as e:
            self.config.log(f"Error saving handoff: {e}")
        
        return handoff
    
    def _get_addon_info(self, addon_path):
        """Extract addon info."""
        info = {'id': '', 'name': '', 'version': '', 'type': 'unknown'}
        
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
            
            # Determine type
            for ext in root.findall('extension'):
                point = ext.get('point', '')
                if 'plugin.video' in point:
                    info['type'] = 'video_plugin'
                elif 'plugin' in point:
                    info['type'] = 'plugin'
                elif 'service' in point:
                    info['type'] = 'service'
                elif 'script' in point:
                    info['type'] = 'script'
        except Exception:
            pass
        
        return info
    
    def _generate_bundle_files(self, bundle_dir, bundle_data):
        """Generate files for the bundle."""
        # 1. Bundle metadata
        meta_path = os.path.join(bundle_dir, 'bundle.json')
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump({
                'name': bundle_data['bundle_name'],
                'created': bundle_data['created'],
                'source_addon': bundle_data['source_addon'],
                'item_count': len(bundle_data['items'])
            }, f, indent=2)
        
        # 2. Code files
        for i, item in enumerate(bundle_data['items']):
            filename = f"{item['name']}_{i}.py"
            filepath = os.path.join(bundle_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f'# Source: {item["original_file"]}\\n')
                f.write(f'# Line: {item["metadata"]["line"]}\\n\\n')
                f.write(item['original_code'])
            
            bundle_data['files_created'].append(filepath)
        
        # 3. Index file
        index_path = os.path.join(bundle_dir, 'INDEX.txt')
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(f"Bundle: {bundle_data['bundle_name']}\\n")
            f.write(f"Source: {bundle_data['source_addon'].get('name', 'Unknown')}\\n")
            f.write(f"Items: {len(bundle_data['items'])}\\n\\n")
            
            for item in bundle_data['items']:
                f.write(f"- {item['name']} ({item['type']})\\n")
                f.write(f"  From: {item['original_file']}:{item['metadata']['line']}\\n")
                if item['metadata']['args']:
                    f.write(f"  Args: {', '.join(item['metadata']['args'])}\\n")
                f.write('\\n')
    
    def _generate_template_files(self, template_dir, template_data):
        """Generate blueprint template files."""
        # 1. Template manifest
        manifest_path = os.path.join(template_dir, 'template.json')
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump({
                'name': template_data['template_name'],
                'type': template_data['pattern_type'],
                'created': template_data['created'],
                'source_addon': template_data['source_addon'],
                'placeholders': template_data['placeholders']
            }, f, indent=2)
        
        # 2. Structure documentation
        struct_path = os.path.join(template_dir, 'STRUCTURE.md')
        with open(struct_path, 'w', encoding='utf-8') as f:
            f.write(f"# {template_data['template_name']}\\n\\n")
            f.write(f"Pattern Type: {template_data['pattern_type']}\\n")
            f.write(f"Source: {template_data['source_addon'].get('name', 'Unknown')}\\n\\n")
            
            f.write("## Directory Structure\\n\\n")
            f.write("```\\n")
            self._write_structure_tree(f, template_data['structure'])
            f.write("```\\n\\n")
            
            f.write("## Placeholders\\n\\n")
            for ph in template_data['placeholders']:
                f.write(f"- `{ph['name']}`: {ph['description']}\\n")
        
        # 3. Starter code
        starter_path = os.path.join(template_dir, 'starter.py')
        with open(starter_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_starter_code(template_data))
    
    def _analyze_structure(self, addon_path, pattern_type):
        """Analyze addon structure for template."""
        structure = {
            'root_files': [],
            'resources': [],
            'lib_modules': [],
            'key_files': {}
        }
        
        # Root files
        for item in os.listdir(addon_path):
            if os.path.isfile(os.path.join(addon_path, item)):
                structure['root_files'].append(item)
        
        # Resources structure
        resources_path = os.path.join(addon_path, 'resources')
        if os.path.exists(resources_path):
            for root, dirs, files in os.walk(resources_path):
                rel_path = os.path.relpath(root, addon_path)
                structure['resources'].append({
                    'path': rel_path,
                    'files': files
                })
        
        # Key files based on pattern type
        if pattern_type == 'video_plugin':
            structure['key_files'] = {
                'entry': 'default.py',
                'router': 'resources/lib/router.py',
                'list_builder': 'resources/lib/list_builder.py',
                'resolver': 'resources/lib/resolver.py'
            }
        
        return structure
    
    def _generate_starter_code(self, template_data):
        """Generate starter code for template."""
        addon_id = template_data['source_addon'].get('id', 'YOUR_ADDON_ID')
        addon_name = template_data['source_addon'].get('name', 'YOUR_ADDON_NAME')
        
        code = f'''"""
{template_data['template_name']}
Based on: {addon_name}
"""
import xbmcaddon

ADDON_ID = '{addon_id}'
ADDON_NAME = '{addon_name}'

class AddonRouter:
    """Main addon router - customize for your needs."""
    
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.handle = 0
    
    def run(self):
        """Main entry point."""
        # TODO: Implement your routing logic
        pass

if __name__ == '__main__':
    router = AddonRouter()
    router.run()
'''
        return code
    
    def _update_bundle_index(self, bundle_data):
        """Update the bundle index."""
        index_path = os.path.join(self.config.cache_path, 'bundle_index.json')
        
        index = []
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    index = json.load(f)
            except Exception:
                pass
        
        index.append({
            'name': bundle_data['bundle_name'],
            'created': bundle_data['created'],
            'source_addon': bundle_data['source_addon'].get('name'),
            'item_count': len(bundle_data['items']),
            'path': bundle_data['bundle_path']
        })
        
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)
    
    def _write_structure_tree(self, f, structure, indent=0):
        """Write directory structure as tree."""
        prefix = "  " * indent
        
        for file in structure.get('root_files', []):
            f.write(f"{prefix}{file}\\n")
        
        for res in structure.get('resources', []):
            f.write(f"{prefix}{res['path']}/\\n")
            for file in res.get('files', []):
                f.write(f"{prefix}  {file}\\n")
    
    def _generate_pattern_summary(self, addon, results):
        """Generate pattern extraction summary."""
        return f"Extracted {len(results.get('functions', []))} functions and {len(results.get('classes', []))} classes from {addon['name']}"
    
    def _extract_key_findings(self, results):
        """Extract key findings from results."""
        findings = []
        
        if 'functions' in results:
            for func in results['functions'][:3]:
                findings.append(f"Function '{func['name']}' in {func['file']}")
        
        return findings
    
    def _extract_snippets(self, results):
        """Extract code snippets for handoff."""
        snippets = []
        
        if 'functions' in results:
            for func in results['functions'][:2]:
                snippets.append({
                    'name': func['name'],
                    'code': func['code'][:500]  # First 500 chars
                })
        
        return snippets
    
    def _generate_hook_summary(self, addon, results):
        """Generate hook analysis summary."""
        entry_points = len(results.get('entry_points', []))
        hooks = len(results.get('hook_functions', []))
        return f"Found {entry_points} entry points and {hooks} hook functions in {addon['name']}"
    
    def _extract_hook_findings(self, results):
        """Extract hook findings."""
        findings = []
        
        for hook in results.get('hook_functions', [])[:5]:
            findings.append(f"Hook '{hook['name']}' ({hook['type']})")
        
        return findings
    
    def _generate_cleaning_summary(self, addon, results):
        """Generate code cleaning summary."""
        changes = results.get('changes_made', {})
        return f"Cleaned {changes.get('lines_changed', 0)} lines from {addon['name']}"
    
    def _generate_recommendations(self, results):
        """Generate recommendations."""
        recs = []
        
        if 'placeholders' in results:
            for ph in results['placeholders']:
                recs.append(f"Replace {ph['name']} with your value")
        
        return recs
    
    def _format_handoff(self, handoff):
        """Format handoff as markdown."""
        lines = []
        
        lines.append(f"## Analysis Handoff: {handoff['addon']['name']}")
        lines.append("")
        lines.append(f"**Type:** {handoff['type']}")
        lines.append(f"**Addon:** {handoff['addon']['id']} v{handoff['addon']['version']}")
        lines.append("")
        
        lines.append("**Summary:**")
        lines.append(handoff['summary'])
        lines.append("")
        
        if handoff['key_findings']:
            lines.append("**Key Findings:**")
            for finding in handoff['key_findings']:
                lines.append(f"- {finding}")
            lines.append("")
        
        if handoff['code_snippets']:
            lines.append("**Code Snippets:**")
            for snippet in handoff['code_snippets']:
                lines.append(f"\\n`{snippet['name']}:`")
                lines.append("```python")
                lines.append(snippet['code'])
                lines.append("```")
            lines.append("")
        
        if handoff['recommendations']:
            lines.append("**Recommendations:**")
            for rec in handoff['recommendations']:
                lines.append(f"1. {rec}")
            lines.append("")
        
        return "\\n".join(lines)
    
    def generate_report(self, addon, bundle_results, bundle_type='bundle'):
        """Generate bundling report."""
        report = f"[B]Code Bundle: {addon['name']}[/B]\\n\\n"
        
        if bundle_type == 'bundle':
            report += f"[B]Bundle:[/B] {bundle_results['bundle_name']}\\n"
            report += f"Items: {len(bundle_results['items'])}\\n"
            report += f"Files created: {len(bundle_results['files_created'])}\\n"
            
            if bundle_results['bundle_path']:
                report += f"\\n[B]Location:[/B] {bundle_results['bundle_path']}\\n"
        
        elif bundle_type == 'template':
            report += f"[B]Template:[/B] {bundle_results['template_name']}\\n"
            report += f"Type: {bundle_results['pattern_type']}\\n"
            
            if bundle_results['placeholders']:
                report += f"\\n[B]Placeholders ({len(bundle_results['placeholders']}):[/B]\\n"
                for ph in bundle_results['placeholders']:
                    report += f"  • {ph['name']}: {ph['description']}\\n"
            
            if bundle_results['template_path']:
                report += f"\\n[B]Location:[/B] {bundle_results['template_path']}\\n"
        
        elif bundle_type == 'handoff':
            report += f"[B]AI Handoff Generated[/B]\\n"
            report += f"Type: {bundle_results['type']}\\n"
            if 'file_path' in bundle_results:
                report += f"Saved: {bundle_results['file_path']}\\n"
        
        return report
'''

print("module_code_bundler.py created")
