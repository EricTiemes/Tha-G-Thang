import sys
import xbmcaddon
from urllib.parse import parse_qsl

# Add lib path
addon = xbmcaddon.Addon()
addon_path = addon.getAddonInfo('path')
sys.path.insert(0, f"{addon_path}/resources/lib")

from core.config import Config
from core.router import Router

def run():
    """Main entry point"""
    handle = int(sys.argv[1])
    params = dict(parse_qsl(sys.argv[2][1:]))
    
    config = Config(addon)
    router = Router(config)
    router.route(handle, params)

if __name__ == '__main__':
    run()