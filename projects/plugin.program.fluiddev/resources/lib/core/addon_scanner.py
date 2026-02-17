"""
FluidDev - Addon Scanner
Core scanner using config environment abstraction.
"""
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime


class AddonScanner:
    """Scans and catalogs installed Kodi addons."""
    
    def __init__(self, config):
        self.config = config
        
    def get_installed_addons(self):
        """Get list of all installed addons."""
        addons = []
        addons_path = self.config.addons_path
        
        if not self.config.vfs_exists(addons_path):
            self.config.log(f"Addons path not found: {addons_path}", 2)
            return addons
        
        try:
            dirs, files = self.config.vfs_listdir(addons_path)
            for addon_dir in dirs:
                addon_path = os.path.join(addons_path, addon_dir)
                addon_xml = os.path.join(addon_path, 'addon.xml')
                if self.config.vfs_exists(addon_xml):
                    addon_info = self._parse_addon_xml(addon_path)
                    if addon_info:
                        addons.append(addon_info)
        except Exception as e:
            self.config.log(f"Error scanning addons: {e}", 3)
        
        return addons
    
    def _parse_addon_xml(self, addon_path):
        """Parse addon.xml and extract metadata."""
        xml_file = os.path.join(addon_path, 'addon.xml')
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            return {
                'id': root.get('id', os.path.basename(addon_path)),
                'name': root.get('name', root.get('id')),
                'version': root.get('version', 'Unknown'),
                'provider': root.get('provider-name', 'Unknown'),
                'path': addon_path,
                'type': self._get_addon_type(root)
            }
        except Exception as e:
            self.config.log(f"Error parsing {xml_file}: {e}", 2)
            return None
    
    def _get_addon_type(self, root):
        """Extract addon type from XML."""
        for extension in root.findall('extension'):
            point = extension.get('point', '')
            if 'plugin' in point:
                return 'plugin'
            elif 'script' in point:
                return 'script'
            elif 'service' in point:
                return 'service'
        return 'unknown'
    
    def save_scan_results(self, results):
        """Save scan results to cache."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"global_scan_{timestamp}.json"
        filepath = os.path.join(self.config.cache_path, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': timestamp,
                    'addon_count': len(results),
                    'results': results
                }, f, indent=2, default=str)
            self.config.log(f"Scan results saved: {filepath}")
            return filepath
        except Exception as e:
            self.config.log(f"Error saving scan results: {e}", 3)
            return None
