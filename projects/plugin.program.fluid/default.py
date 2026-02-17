# ruff: noqa: E402
import sys
import os
import xbmcvfs

addon_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(addon_path, 'resources', 'lib'))

from core.router import router
from core.logger import logger


def _register_modules():
    """
    Auto-discover modules and register their routes with the router.
    Each module that exposes MODULE_ROUTES dict gets registered automatically.
    """
    from modules import discover_modules, load_module

    for module_info in discover_modules():
        mod_id = module_info['id']
        module = load_module(mod_id)
        if module is None:
            continue
        for entry in ('builder', 'manager', 'engine', 'router'):
            try:
                sub = __import__(
                    f'modules.{mod_id}.{entry}',
                    fromlist=['MODULE_ROUTES']
                )
                routes = getattr(sub, 'MODULE_ROUTES', None)
                if routes:
                    router.register_module_routes(mod_id, routes)
                    logger.debug(f"Registered routes for {mod_id}.{entry}: {list(routes.keys())}")
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Route registration failed for {mod_id}.{entry}: {e}")


def _run_first_run_wizard():
    """
    One-time setup wizard shown on first install.
    Covers: settings mode, download path, delivery path.
    Minimal — user can always change everything in Settings.
    """
    import xbmcgui
    import xbmc
    from core.config import config

    dlg = xbmcgui.Dialog()

    # Welcome
    dlg.ok(
        'Welcome to FLUID',
        'Quick setup — 3 steps.\nYou can change everything later in Settings.'
    )

    # Step 1: Settings mode
    mode_choice = dlg.select(
        'Step 1 of 3 — How do you want to use FLUID?',
        [
            'Simple  —  one-tap download, minimal options',
            'Advanced  —  control quality, delivery, privacy',
            'Pro  —  full control + debug tools',
        ]
    )
    if mode_choice < 0:
        mode_choice = 0   # cancelled = simple
    mode = ['simple', 'advanced', 'pro'][mode_choice]
    config.set_setting('settings_mode', mode)

    # Step 2: Download folder
    download_path = dlg.browse(
        0, 'Step 2 of 3 — Where should downloads be saved?',
        'files', '', False, False,
        xbmcvfs.translatePath('special://temp/fluid')
    )
    if download_path:
        setting_key = 'simple_download_path' if mode == 'simple' else 'download_path'
        config.set_setting(setting_key, download_path)

    # Step 3: Auto-deliver toggle (simple) or delivery path (advanced/pro)
    if mode == 'simple':
        auto_deliver = dlg.yesno(
            'Step 3 of 3 — Auto-deliver?',
            'Automatically copy downloads to your Videos folder?'
        )
        config.set_setting('simple_auto_deliver', auto_deliver)
    else:
        dlg.ok(
            'Step 3 of 3 — Delivery Paths',
            'Set up keyword-based delivery rules in:\nSettings > Delivery Paths\n\nYou can route music, clips etc. to separate folders automatically.'
        )

    # Mark wizard complete
    config.set_setting('first_run', False)

    dlg.ok(
        'All set!',
        'FLUID is ready.\nRight-click any video to download.'
    )


def main():
    """Main entry point for plugin/script calls."""
    try:
        from core.config import config

        # First-run wizard — once only
        if config.get_setting('first_run', True):
            _run_first_run_wizard()

        # Register module routes before dispatching
        _register_modules()

        url_string = sys.argv[2][1:] if len(sys.argv) > 2 else ''
        logger.debug(f"FLUID started with params: {url_string}")
        router.dispatch(url_string)

    except Exception as e:
        logger.error(f"Main error: {e}")
        import xbmcgui
        xbmcgui.Dialog().notification('FLUID Error', str(e), xbmcgui.NOTIFICATION_ERROR)


if __name__ == '__main__':
    main()
