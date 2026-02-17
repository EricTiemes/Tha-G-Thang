'''"""
FluidDev - Pattern Extractor Module
AST-based code extraction for deep research.
Extracts functions, classes, and patterns from addon code.
"""
import os
import ast
import re
import xbmcvfs
from pathlib import Path


class PatternExtractor:
    """Extracts code patterns using AST analysis."""
    
    def __init__(self, config):
        self.config = config
        self.extracted_patterns = []
        
    def extract_by_name_pattern(self, addon_path, pattern):
        """Extract functions/classes matching name pattern (regex)."""
        results = {
            'functions': [],
            'classes': [],
            'files_searched': 0
        }
        
        py_files = self._get_python_files(addon_path)
        results['files_searched'] = len(py_files)
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    rel_path = os.path.relpath(py_file, addon_path)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if re.search(pattern, node.name, re.IGNORECASE):
                                func_code = self._extract_function_code(content, node)
                                results['functions'].append({
                                    'name': node.name,
                                    'file': rel_path,
                                    'line': node.lineno,
                                    'code': func_code,
                                    'args': [arg.arg for arg in node.args.args]
                                })
                        
                        elif isinstance(node, ast.ClassDef):
                            if re.search(pattern, node.name, re.IGNORECASE):
                                class_code = self._extract_class_code(content, node)
                                results['classes'].append({
                                    'name': node.name,
                                    'file': rel_path,
                                    'line': node.lineno,
                                    'code': class_code,
                                    'bases': [self._get_base_name(base) for base in node.bases]
                                })
            except SyntaxError:
                continue
            except Exception as e:
                self.config.log(f"Error parsing {py_file}: {e}")
                continue
        
        return results
    
    def extract_by_api_usage(self, addon_path, api_pattern):
        """Extract all functions that use a specific API (e.g., 'xbmcgui.Dialog')."""
        results = {
            'functions': [],
            'api_calls': [],
            'files_searched': 0
        }
        
        py_files = self._get_python_files(addon_path)
        results['files_searched'] = len(py_files)
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    rel_path = os.path.relpath(py_file, addon_path)
                    
                    # Find all function definitions
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            func_code = self._extract_function_code(content, node)
                            
                            # Check if function uses the API
                            if api_pattern in func_code:
                                # Find specific API calls
                                api_calls = self._find_api_calls(func_code, api_pattern)
                                
                                results['functions'].append({
                                    'name': node.name,
                                    'file': rel_path,
                                    'line': node.lineno,
                                    'code': func_code,
                                    'api_calls': api_calls
                                })
            except SyntaxError:
                continue
            except Exception as e:
                self.config.log(f"Error analyzing {py_file}: {e}")
                continue
        
        return results
    
    def extract_by_decorator(self, addon_path, decorator_pattern):
        """Extract functions with specific decorators (e.g., '@route')."""
        results = {
            'functions': [],
            'files_searched': 0
        }
        
        py_files = self._get_python_files(addon_path)
        results['files_searched'] = len(py_files)
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    rel_path = os.path.relpath(py_file, addon_path)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            # Check decorators
                            for decorator in node.decorator_list:
                                dec_name = self._get_decorator_name(decorator)
                                if re.search(decorator_pattern, dec_name, re.IGNORECASE):
                                    func_code = self._extract_function_code(content, node)
                                    results['functions'].append({
                                        'name': node.name,
                                        'file': rel_path,
                                        'line': node.lineno,
                                        'code': func_code,
                                        'decorator': dec_name,
                                        'args': [arg.arg for arg in node.args.args]
                                    })
            except SyntaxError:
                continue
            except Exception as e:
                self.config.log(f"Error parsing {py_file}: {e}")
                continue
        
        return results
    
    def extract_imports_tree(self, addon_path):
        """Extract complete import tree from addon."""
        results = {
            'imports': [],
            'from_imports': [],
            'local_imports': [],
            'files_searched': 0
        }
        
        py_files = self._get_python_files(addon_path)
        results['files_searched'] = len(py_files)
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    tree = ast.parse(f.read())
                    rel_path = os.path.relpath(py_file, addon_path)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                results['imports'].append({
                                    'module': alias.name,
                                    'asname': alias.asname,
                                    'file': rel_path,
                                    'line': node.lineno
                                })
                        
                        elif isinstance(node, ast.ImportFrom):
                            module = node.module or ''
                            names = [alias.name for alias in node.names]
                            
                            import_info = {
                                'module': module,
                                'names': names,
                                'file': rel_path,
                                'line': node.lineno
                            }
                            
                            # Categorize as local or external
                            if module.startswith('.') or 'resources.lib' in module:
                                results['local_imports'].append(import_info)
                            else:
                                results['from_imports'].append(import_info)
            except SyntaxError:
                continue
            except Exception as e:
                self.config.log(f"Error parsing {py_file}: {e}")
                continue
        
        return results
    
    def _get_python_files(self, addon_path, limit=100):
        """Get all Python files in addon."""
        files = []
        try:
            for root, dirs, filenames in os.walk(addon_path):
                # Skip __pycache__
                dirs[:] = [d for d in dirs if d != '__pycache__']
                
                for f in filenames:
                    if f.endswith('.py'):
                        files.append(os.path.join(root, f))
                        if len(files) >= limit:
                            return files
        except Exception as e:
            self.config.log(f"Error walking {addon_path}: {e}")
        
        return files
    
    def _extract_function_code(self, content, node):
        """Extract function source code from AST node."""
        lines = content.split('\n')
        start_line = node.lineno - 1
        
        # Find end line (simple approach)
        end_line = start_line
        base_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
        
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip() and not line.strip().startswith('#'):
                indent = len(line) - len(line.lstrip())
                if indent <= base_indent and not line.strip().startswith('def ') and not line.strip().startswith('class '):
                    break
            end_line = i
        
        return '\n'.join(lines[start_line:end_line + 1])
    
    def _extract_class_code(self, content, node):
        """Extract class source code from AST node."""
        return self._extract_function_code(content, node)
    
    def _get_base_name(self, base):
        """Get base class name from AST node."""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return f"{self._get_base_name(base.value)}.{base.attr}"
        return str(base)
    
    def _get_decorator_name(self, decorator):
        """Get decorator name from AST node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_decorator_name(decorator.value)}.{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return str(decorator)
    
    def _find_api_calls(self, code, api_pattern):
        """Find specific API calls in code."""
        calls = []
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if api_pattern in line:
                calls.append({
                    'line': i,
                    'code': line.strip()
                })
        return calls
    
    def generate_report(self, addon, extraction_results, extraction_type):
        """Generate human-readable extraction report."""
        report = f"[B]Pattern Extraction: {addon['name']}[/B]\\n"
        report += f"Type: {extraction_type}\\n"
        report += f"Files searched: {extraction_results.get('files_searched', 0)}\\n\\n"
        
        if 'functions' in extraction_results and extraction_results['functions']:
            report += f"[B]Functions Found ({len(extraction_results['functions'])}):[/B]\\n"
            for func in extraction_results['functions'][:10]:  # Limit to 10
                report += f"\\n  [COLOR teal]{func['name']}[/COLOR]\\n"
                report += f"  File: {func['file']}:{func['line']}\\n"
                if 'args' in func:
                    report += f"  Args: {', '.join(func['args'])}\\n"
                if 'decorator' in func:
                    report += f"  Decorator: @{func['decorator']}\\n"
                if 'api_calls' in func:
                    report += f"  API Calls: {len(func['api_calls'])}\\n"
                
                # Show code preview (first 3 lines)
                code_lines = func['code'].split('\\n')[:3]
                report += "  Preview:\\n"
                for line in code_lines:
                    report += f"    {line}\\n"
                report += "\\n"
        
        if 'classes' in extraction_results and extraction_results['classes']:
            report += f"\\n[B]Classes Found ({len(extraction_results['classes'])}):[/B]\\n"
            for cls in extraction_results['classes'][:5]:  # Limit to 5
                report += f"\\n  [COLOR teal]{cls['name']}[/COLOR]\\n"
                report += f"  File: {cls['file']}:{cls['line']}\\n"
                if cls['bases']:
                    report += f"  Bases: {', '.join(cls['bases'])}\\n"
        
        if 'imports' in extraction_results:
            report += f"\\n[B]Import Summary:[/B]\\n"
            report += f"  Total imports: {len(extraction_results['imports'])}\\n"
            report += f"  From imports: {len(extraction_results['from_imports'])}\\n"
            report += f"  Local imports: {len(extraction_results['local_imports'])}\\n"
        
        return report
'''

print("module_pattern_extractor.py created")
