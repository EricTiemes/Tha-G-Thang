"""
FluidDev - Structure Analyzer Module
Analyzes addon structure using config environment.
"""
import os
import xml.etree.ElementTree as ET


class StructureAnalyzer:
    """Analyzes addon structure and architecture patterns."""
    
    def __init__(self, config):
        self.config = config
        self.framework_indicators = {
            'routing': ['import routing', 'from routing'],
            'simpleplugin': ['import simpleplugin'],
            'codequick': ['from codequick', 'import codequick'],
            'xbmcswift2': ['import xbmcswift'],
            'pyxbmct': ['import pyxbmct']
        }
    
    def analyze(self, addon_path):
        """Perform structure analysis on an addon."""
        result = {
            'module_count': 0,
            'has_lib_folder': False,
            'frameworks': [],
            'entry_point': None,
            'structure_type': 'unknown'
        }
        
        lib_path = os.path.join(addon_path, 'resources', 'lib')
        if self.config.vfs_exists(lib_path):
            result['has_lib_folder'] = True
            result['module_count'] = self._count_python_files(lib_path)
        
        for pattern in ['default.py', 'addon.py', 'plugin.py', 'main.py', 'service.py']:
            entry_file = os.path.join(addon_path, pattern)
            if self.config.vfs_exists(entry_file):
                result['entry_point'] = pattern
                break
        
        result['frameworks'] = self._detect_frameworks(addon_path)
        result['structure_type'] = self._classify_structure(result)
        return result
    
    def _count_python_files(self, path):
        """Count Python files in directory recursively."""
        count = 0
        try:
            dirs, files = self.config.vfs_listdir(path)
            for f in files:
                if f.endswith('.py'):
                    count += 1
            for d in dirs:
                count += self._count_python_files(os.path.join(path, d))
        except Exception:
            pass
        return count
    
    def _detect_frameworks(self, addon_path):
        """Detect frameworks used by the addon."""
        frameworks = set()
        xml_file = os.path.join(addon_path, 'addon.xml')
        if self.config.vfs_exists(xml_file):
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                for requires in root.findall('requires'):
                    for imp in requires.findall('import'):
                        addon = imp.get('addon', '')
                        if 'script.module.' in addon:
                            for fw in self.framework_indicators.keys():
                                if fw in addon:
                                    frameworks.add(fw)
            except Exception:
                pass
        
        py_files = self._get_sample_python_files(addon_path, 5)
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    for fw, indicators in self.framework_indicators.items():
                        if any(ind in content for ind in indicators):
                            frameworks.add(fw)
            except Exception:
                pass
        
        return list(frameworks)
    
    def _get_sample_python_files(self, path, limit=5):
        """Get sample of Python files for analysis."""
        files = []
        try:
            self._collect_py_files(path, files, limit)
        except Exception:
            pass
        return files[:limit]
    
    def _collect_py_files(self, path, files, limit):
        """Recursively collect Python files."""
        if len(files) >= limit:
            return
        try:
            dirs, filenames = self.config.vfs_listdir(path)
            for f in filenames:
                if f.endswith('.py'):
                    files.append(os.path.join(path, f))
                    if len(files) >= limit:
                        return
            for d in dirs:
                self._collect_py_files(os.path.join(path, d), files, limit)
        except Exception:
            pass
    
    def _classify_structure(self, analysis):
        """Classify addon structure type."""
        if analysis['module_count'] > 20:
            return 'highly_modular'
        elif analysis['module_count'] > 10:
            return 'modular'
        elif analysis['has_lib_folder']:
            return 'structured'
        else:
            return 'simple'
    
    def generate_snapshot(self, addon, analysis):
        """Generate human-readable snapshot."""
        snapshot = f"[B]{addon['name']}[/B]\\n"
        snapshot += f"ID: {addon['id']}\\n"
        snapshot += f"Version: {addon['version']}\\n\\n"
        snapshot += "[B]Structure Analysis:[/B]\\n"
        snapshot += f"  Type: {analysis['structure_type']}\\n"
        snapshot += f"  Modules: {analysis['module_count']}\\n"
        snapshot += f"  Entry Point: {analysis.get('entry_point', 'Unknown')}\\n"
        if analysis['frameworks']:
            snapshot += "\\n[B]Frameworks:[/B]\\n"
            for fw in analysis['frameworks']:
                snapshot += f"  • {fw}\\n"
        return snapshot
    
    def find_similar(self, reference_addon, all_addons):
        """Find addons with similar structure."""
        ref_analysis = self.analyze(reference_addon['path'])
        similar = []
        for addon in all_addons:
            if addon['id'] == reference_addon['id']:
                continue
            analysis = self.analyze(addon['path'])
            score = self._calculate_similarity(ref_analysis, analysis)
            if score > 30:
                similar.append({
                    'name': addon['name'],
                    'id': addon['id'],
                    'similarity_score': score
                })
        return sorted(similar, key=lambda x: x['similarity_score'], reverse=True)
    
    def _calculate_similarity(self, a1, a2):
        """Calculate similarity score between two analyses."""
        score = 0
        if a1['module_count'] > 0 and a2['module_count'] > 0:
            ratio = min(a1['module_count'], a2['module_count']) / max(a1['module_count'], a2['module_count'])
            score += ratio * 30
        if a1['structure_type'] == a2['structure_type']:
            score += 30
        common_fw = set(a1['frameworks']) & set(a2['frameworks'])
        if common_fw:
            score += len(common_fw) * 20
        return int(score)
