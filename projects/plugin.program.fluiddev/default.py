import sys
from resources.entry_router import EntryRouter

if __name__ == '__main__':
    router = EntryRouter()
    router.route(sys.argv)