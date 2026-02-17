"""
FluidDev - Dependency Mapper Module
Analyzes addon dependencies from addon.xml and Python imports.
"""
import os
import re
import xml.etree.ElementTree as ET
import xbmcvfs

class DependencyMapper:
    """Maps and analyzes addon dependencies."""
    
    def __init__(self, config):
        self.config = config
        
    def analyze(self, addon_path):
        """Basic dependency analysis."""
        return {
            'xml_dependencies': self._parse_xml_dependencies(addon_path),
            'import_count': self._count_imports(addon_path)
        }
    
    def deep_analyze(self, addon_path):
        """Deep dependency analysis."""
        result = {
            'xml_dependencies': self._parse_xml_dependencies(addon_path),
            'python_imports': self._analyze_imports(addon_path),
            'unofficial_repos': [],
            'missing_dependencies': []
        }
        
        # Check for unofficial repo dependencies
        for dep in result['xml_dependencies']:
            if self._is_unofficial(dep):
                result['unofficial_repos'].append(dep)
        
        return result
    
    def _parse_xml_dependencies(self, addon_path):
        """Parse dependencies from addon.xml."""
        deps = []
        xml_file = os.path.join(addon_path, 'addon.xml')
        
        if not xbmcvfs.exists(xml_file):
            return deps
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            for requires in root.findall('requires'):
                for imp in requires.findall('import'):
                    addon = imp.get('addon', '')
                    version = imp.get('version', '')
                    optional = imp.get('optional', 'false')
                    
                    deps.append({
                        'addon': addon,
                        'version': version,
                        'optional': optional == 'true'
                    })
        except Exception as e:
            self.config.log(f"Error parsing dependencies: {e}")
        
        return deps
    
    def _count_imports(self, addon_path):
        """Count Python imports in addon."""
        count = 0
        lib_path = os.path.join(addon_path, 'resources', 'lib')
        
        if xbmcvfs.exists(lib_path):
            py_files = self._get_python_files(lib_path, limit=10)
            for py_file in py_files:
                count += self._count_imports_in_file(py_file)
        
        return count
    
    def _analyze_imports(self, addon_path):
        """Analyze all Python imports."""
        imports = {
            'stdlib': [],
            'xbmc': [],
            'third_party': [],
            'local': []
        }
        
        lib_path = os.path.join(addon_path, 'resources', 'lib')
        if xbmcvfs.exists(lib_path):
            py_files = self._get_python_files(lib_path, limit=20)
            
            for py_file in py_files:
                file_imports = self._extract_imports(py_file)
                for imp in file_imports:
                    category = self._categorize_import(imp)
                    if imp not in imports[category]:
                        imports[category].append(imp)
        
        return imports
    
    def _get_python_files(self, path, limit=20):
        """Get Python files from directory."""
        files = []
        self._collect_files(path, files, limit)
        return files[:limit]
    
    def _collect_files(self, path, files, limit):
        """Recursively collect Python files."""
        if len(files) >= limit:
            return
        
        try:
            dirs, filenames = xbmcvfs.listdir(path)
            for f in filenames:
                if f.endswith('.py'):
                    files.append(os.path.join(path, f))
                    if len(files) >= limit:
                        return
            for d in dirs:
                self._collect_files(os.path.join(path, d), files, limit)
        except Exception:
            pass
    
    def _count_imports_in_file(self, filepath):
        """Count imports in a single file."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return len(re.findall(r'^(?:from|import)\s+\w+', content, re.MULTILINE))
        except Exception:
            return 0
    
    def _extract_imports(self, filepath):
        """Extract all imports from a file."""
        imports = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        # Extract module name
                        match = re.match(r'(?:from|import)\s+([\w.]+)', line)
                        if match:
                            imports.append(match.group(1))
        except Exception:
            pass
        return imports
    
    def _categorize_import(self, imp):
        """Categorize import type."""
        if imp.startswith('xbmc'):
            return 'xbmc'
        elif imp in ['os', 'sys', 're', 'json', 'time', 'datetime', 'urllib', 'xml', 'html']:
            return 'stdlib'
        elif '.' in imp and not imp.startswith('xbmc'):
            return 'local'
        else:
            return 'third_party'
    
    def _is_unofficial(self, dep):
        """Check if dependency is from unofficial repo."""
        # Simple heuristic: unofficial if not in common repos
        addon = dep['addon']
        
        # Known unofficial indicators
        unofficial_indicators = ['tvaddons', 'supremacy', 'lambda']
        
        return any(ind in addon.lower() for ind in unofficial_indicators)
    
    def generate_report(self, addon, analysis):
        """Generate dependency report."""
        report = f"[B]Dependency Analysis: {addon['name']}[/B]\n\n"
        
        report += "[B]XML Dependencies:[/B]\n"
        if analysis['xml_dependencies']:
            for dep in analysis['xml_dependencies']:
                optional = " (optional)" if dep['optional'] else ""
                report += f"  • {dep['addon']} v{dep['version']}{optional}\n"
        else:
            report += "  None found\n"
        
        if analysis.get('python_imports'):
            imports = analysis['python_imports']
            report += "\n[B]Python Imports:[/B]\n"
            
            if imports['xbmc']:
                report += f"  XBMC modules: {len(imports['xbmc'])}\n"
            if imports['third_party']:
                report += f"  Third-party: {len(imports['third_party'])}\n"
                report += f"    Examples: {', '.join(imports['third_party'][:5])}\n"
            if imports['local']:
                report += f"  Local modules: {len(imports['local'])}\n"
        
        if analysis.get('unofficial_repos'):
            report += "\n[COLOR yellow][B]⚠ Unofficial Repository Dependencies:[/B][/COLOR]\n"
            for dep in analysis['unofficial_repos']:
                report += f"  • {dep['addon']}\n"
        
        return report
