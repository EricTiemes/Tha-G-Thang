"""
FLUID Modules Package
Auto-discovered modules: downloader, delivery, favorites, playlist, meta
"""
import os
import json


def discover_modules() -> list:
    """
    Auto-discover available modules by scanning this package's directory.
    A valid module is a subdirectory containing an __init__.py.
    Optional module.json provides display name and metadata.
    """
    modules = []
    modules_path = os.path.dirname(os.path.abspath(__file__))

    for item in sorted(os.listdir(modules_path)):
        item_path = os.path.join(modules_path, item)
        if not os.path.isdir(item_path) or item.startswith('__'):
            continue

        init_file = os.path.join(item_path, '__init__.py')
        if not os.path.exists(init_file):
            continue

        module_info = {'id': item, 'name': item.title()}

        manifest = os.path.join(item_path, 'module.json')
        if os.path.exists(manifest):
            try:
                with open(manifest, 'r') as f:
                    module_info.update(json.load(f))
            except Exception:
                pass

        modules.append(module_info)

    return modules


def load_module(module_id: str):
    """Dynamically load a module package; returns module or None."""
    try:
        return __import__(f'modules.{module_id}', fromlist=['*'])
    except ImportError as e:
        from core.logger import logger
        logger.error(f"Failed to load module {module_id}: {e}")
        return None


__all__ = ['discover_modules', 'load_module']