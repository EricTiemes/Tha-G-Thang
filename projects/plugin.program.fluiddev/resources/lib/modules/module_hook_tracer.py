'''"""
FluidDev - Hook Tracer Module
Traces execution flows and identifies hook functions in addons.
"""
import os
import ast
import re
import xbmcvfs


class HookTracer:
    """Traces execution paths and identifies hook functions."""
    
    def __init__(self, config):
        self.config = config
        self.call_graph = {}
        self.entry_points = []
        self.hook_functions = []
        
    def trace_addon_flow(self, addon_path):
        """Complete execution flow analysis of an addon."""
        results = {
            'entry_points': [],
            'call_graph': {},
            'hook_functions': [],
            'unreachable_functions': [],
            'framework_hooks': [],
            'files_analyzed': 0
        }
        
        py_files = self._get_python_files(addon_path)
        results['files_analyzed'] = len(py_files)
        
        # Phase 1: Identify entry points
        results['entry_points'] = self._find_entry_points(addon_path, py_files)
        
        # Phase 2: Build call graph
        results['call_graph'] = self._build_call_graph(py_files)
        
        # Phase 3: Identify hook functions
        results['hook_functions'] = self._identify_hooks(py_files, results['call_graph'])
        
        # Phase 4: Find framework-specific hooks
        results['framework_hooks'] = self._find_framework_hooks(py_files)
        
        # Phase 5: Find unreachable functions
        all_functions = self._get_all_functions(py_files)
        called_functions = set()
        for calls in results['call_graph'].values():
            called_functions.update(calls)
        
        results['unreachable_functions'] = [
            f for f in all_functions 
            if f['name'] not in called_functions and not f['name'].startswith('_')
        ]
        
        return results
    
    def trace_function_calls(self, addon_path, function_name):
        """Trace all calls to/from a specific function."""
        results = {
            'function': function_name,
            'definition': None,
            'called_by': [],
            'calls_to': [],
            'call_chain': []
        }
        
        py_files = self._get_python_files(addon_path)
        
        # Find function definition
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    rel_path = os.path.relpath(py_file, addon_path)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef) and node.name == function_name:
                            results['definition'] = {
                                'file': rel_path,
                                'line': node.lineno,
                                'args': [arg.arg for arg in node.args.args]
                            }
                            
                            # Find what this function calls
                            for child in ast.walk(node):
                                if isinstance(child, ast.Call):
                                    called_func = self._get_call_name(child)
                                    if called_func:
                                        results['calls_to'].append({
                                            'function': called_func,
                                            'line': child.lineno
                                        })
            except Exception:
                continue
        
        # Find what calls this function
        call_graph = self._build_call_graph(py_files)
        for caller, callees in call_graph.items():
            if function_name in callees:
                results['called_by'].append(caller)
        
        return results
    
    def find_routing_patterns(self, addon_path):
        """Find all routing patterns in addon (for URL routing)."""
        results = {
            'routes': [],
            'handlers': [],
            'routing_framework': None
        }
        
        py_files = self._get_python_files(addon_path)
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    rel_path = os.path.relpath(py_file, addon_path)
                    
                    # Detect routing framework
                    if 'import routing' in content or 'from routing' in content:
                        results['routing_framework'] = 'routing'
                    elif 'import simpleplugin' in content:
                        results['routing_framework'] = 'simpleplugin'
                    elif 'from codequick' in content:
                        results['routing_framework'] = 'codequick'
                    
                    # Parse for route decorators
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            for decorator in node.decorator_list:
                                dec_info = self._analyze_route_decorator(decorator)
                                if dec_info:
                                    results['routes'].append({
                                        'path': dec_info.get('path', 'unknown'),
                                        'function': node.name,
                                        'file': rel_path,
                                        'line': node.lineno,
                                        'methods': dec_info.get('methods', [])
                                    })
                                    results['handlers'].append({
                                        'name': node.name,
                                        'route': dec_info.get('path'),
                                        'args': [arg.arg for arg in node.args.args]
                                    })
            except Exception:
                continue
        
        return results
    
    def _find_entry_points(self, addon_path, py_files):
        """Identify addon entry points."""
        entry_points = []
        
        # Check for standard entry point files
        standard_entries = ['default.py', 'addon.py', 'plugin.py', 'main.py', 'service.py']
        
        for entry_file in standard_entries:
            full_path = os.path.join(addon_path, entry_file)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        # Find if __name__ == '__main__' or direct execution
                        has_main_guard = "if __name__ == '__main__':" in content or 'if __name__=="__main__":' in content
                        has_direct_run = 'xbmcplugin.endOfDirectory' in content or 'router.route' in content
                        
                        entry_points.append({
                            'file': entry_file,
                            'type': 'standard',
                            'has_main_guard': has_main_guard,
                            'has_direct_run': has_direct_run
                        })
                except Exception:
                    entry_points.append({
                        'file': entry_file,
                        'type': 'standard',
                        'has_main_guard': False,
                        'has_direct_run': False
                    })
        
        return entry_points
    
    def _build_call_graph(self, py_files):
        """Build a call graph of all functions."""
        call_graph = {}
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    tree = ast.parse(f.read())
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            caller = node.name
                            callees = []
                            
                            for child in ast.walk(node):
                                if isinstance(child, ast.Call):
                                    called_name = self._get_call_name(child)
                                    if called_name:
                                        callees.append(called_name)
                            
                            if callees:
                                call_graph[caller] = list(set(callees))
            except Exception:
                continue
        
        return call_graph
    
    def _identify_hooks(self, py_files, call_graph):
        """Identify hook functions (called by framework but not by user code)."""
        hooks = []
        
        # Functions that are called but don't call others (leaf nodes)
        # or are called by many different functions
        call_counts = {}
        for caller, callees in call_graph.items():
            for callee in callees:
                call_counts[callee] = call_counts.get(callee, 0) + 1
        
        # High call count = likely a utility/hook function
        for func_name, count in call_counts.items():
            if count >= 3:  # Called by 3+ different functions
                hooks.append({
                    'name': func_name,
                    'type': 'utility_hook',
                    'called_by_count': count
                })
        
        # Also check for decorator-based hooks
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    tree = ast.parse(f.read())
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            for decorator in node.decorator_list:
                                dec_name = self._get_decorator_name(decorator)
                                if any(hook_type in dec_name for hook_type in ['route', 'hook', 'handler', 'callback', 'event']):
                                    hooks.append({
                                        'name': node.name,
                                        'type': f'{dec_name}_hook',
                                        'decorator': dec_name
                                    })
            except Exception:
                continue
        
        return hooks
    
    def _find_framework_hooks(self, py_files):
        """Find framework-specific hook implementations."""
        framework_hooks = []
        
        hook_signatures = {
            'xbmc': [
                'onAction', 'onClick', 'onFocus', 'onInit',
                'onSettingsChanged', 'onNotification'
            ],
            'simpleplugin': [
                'action', 'list_item', 'play'
            ],
            'routing': [
                'route', 'run'
            ]
        }
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    tree = ast.parse(f.read())
                    rel_path = os.path.relpath(py_file, os.path.dirname(py_file))
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            for framework, signatures in hook_signatures.items():
                                if node.name in signatures:
                                    framework_hooks.append({
                                        'name': node.name,
                                        'framework': framework,
                                        'file': rel_path,
                                        'line': node.lineno
                                    })
            except Exception:
                continue
        
        return framework_hooks
    
    def _get_all_functions(self, py_files):
        """Get all function definitions."""
        functions = []
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    tree = ast.parse(f.read())
                    rel_path = os.path.relpath(py_file, os.path.dirname(py_file))
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            functions.append({
                                'name': node.name,
                                'file': rel_path,
                                'line': node.lineno
                            })
            except Exception:
                continue
        
        return functions
    
    def _get_python_files(self, addon_path, limit=100):
        """Get all Python files."""
        files = []
        try:
            for root, dirs, filenames in os.walk(addon_path):
                dirs[:] = [d for d in dirs if d != '__pycache__']
                for f in filenames:
                    if f.endswith('.py'):
                        files.append(os.path.join(root, f))
                        if len(files) >= limit:
                            return files
        except Exception as e:
            self.config.log(f"Error walking {addon_path}: {e}")
        return files
    
    def _get_call_name(self, call_node):
        """Extract function name from call node."""
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr
        return None
    
    def _get_decorator_name(self, decorator):
        """Get decorator name."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_decorator_name(decorator.value)}.{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return str(decorator)
    
    def _analyze_route_decorator(self, decorator):
        """Analyze route decorator for path and methods."""
        info = {'path': None, 'methods': []}
        
        if isinstance(decorator, ast.Call):
            # @route('/path') or @route('/path', methods=['GET'])
            if decorator.args:
                first_arg = decorator.args[0]
                if isinstance(first_arg, ast.Constant):
                    info['path'] = first_arg.value
                elif isinstance(first_arg, ast.Str):  # Python < 3.8
                    info['path'] = first_arg.s
            
            # Check for methods keyword
            for keyword in decorator.keywords:
                if keyword.arg == 'methods':
                    if isinstance(keyword.value, ast.List):
                        for elt in keyword.value.elts:
                            if isinstance(elt, ast.Constant):
                                info['methods'].append(elt.value)
                            elif isinstance(elt, ast.Str):
                                info['methods'].append(elt.s)
        
        return info
    
    def generate_report(self, addon, trace_results):
        """Generate execution flow report."""
        report = f"[B]Execution Flow Analysis: {addon['name']}[/B]\\n\\n"
        
        # Entry Points
        report += "[B]Entry Points:[/B]\\n"
        for ep in trace_results['entry_points']:
            report += f"  • {ep['file']}"
            if ep['has_main_guard']:
                report += " [COLOR green](main guard)[/COLOR]"
            if ep['has_direct_run']:
                report += " [COLOR teal](direct run)[/COLOR]"
            report += "\\n"
        
        # Routing
        if trace_results.get('framework_hooks'):
            report += f"\\n[B]Framework Hooks ({len(trace_results['framework_hooks']}):[/B]\\n"
            for hook in trace_results['framework_hooks'][:10]:
                report += f"  • [COLOR teal]{hook['name']}[/COLOR] ({hook['framework']})\\n"
                report += f"    {hook['file']}:{hook['line']}\\n"
        
        # Hook Functions
        if trace_results['hook_functions']:
            report += f"\\n[B]Hook Functions ({len(trace_results['hook_functions']}):[/B]\\n"
            for hook in trace_results['hook_functions'][:10]:
                report += f"  • {hook['name']} [{hook['type']}]"
                if 'called_by_count' in hook:
                    report += f" - called by {hook['called_by_count']} functions"
                report += "\\n"
        
        # Call Graph Summary
        if trace_results['call_graph']:
            report += f"\\n[B]Call Graph:[/B]\\n"
            report += f"  Total functions: {len(trace_results['call_graph'])}\\n"
            
            # Find most connected functions
            connections = {k: len(v) for k, v in trace_results['call_graph'].items()}
            top_connected = sorted(connections.items(), key=lambda x: x[1], reverse=True)[:5]
            
            report += "\\n  Most connected functions:\\n"
            for func_name, count in top_connected:
                report += f"    {func_name}: {count} calls\\n"
        
        # Unreachable functions
        if trace_results['unreachable_functions']:
            report += f"\\n[B]Potentially Unused Functions ({len(trace_results['unreachable_functions']}):[/B]\\n"
            for func in trace_results['unreachable_functions'][:5]:
                report += f"  • {func['name']} in {func['file']}\\n"
        
        return report
'''

print("module_hook_tracer.py created")
