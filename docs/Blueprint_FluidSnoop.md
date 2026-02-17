FluidSnoop – Detailed Blueprint

Product definition

> FluidSnoop is a live runtime snoop & pattern extractor for Kodi addons.
It observes real behavior (UI, DB, network, playback, filesystem) of running addons, reconstructs the working logic, and exports it as reusable code + reports.



It is not a debugger and not static analysis — it is a behavior recorder + code pattern generator.


---

1. Core Goals

Capability	Purpose

Hook live addons	Observe real runtime behavior
Capture flows	User click → network → DB → UI
Extract patterns	Convert logs into reusable logic
Multi-format output	JSON, AI-handoff, compact, detailed
Zero-mod & mod modes	External hooks + optional code injection



---

2. System Architecture

plugin.program.fluidsnoop/
├── addon.py                # dumb router
├── resources/lib/
│   ├── core/
│   │   ├── config.py       # paths, filters, toggles
│   │   ├── logger.py       # structured event writer
│   │   └── router.py
│   └── modules/
│       ├── runtime_hook.py      # monkey patch import & functions
│       ├── call_logger.py       # structured logging
│       ├── ui_interceptor.py    # Dialog, Notification, Progress
│       ├── db_spy.py            # sqlite cursor wrapper
│       ├── network_monitor.py  # requests, urllib, xbmcvfs
│       ├── fs_monitor.py        # file writes, copies, deletes
│       ├── pattern_extractor.py
│       ├── exporter.py
│       └── code_injector.py     # optional inline instrumentation

Router never contains logic, only dispatch.


---

3. Runtime Hook Layer

3.1 Import & Function Spy

# runtime_hook.py
import builtins, sys
orig_import = builtins.__import__

def spy_import(name, *args, **kwargs):
    module = orig_import(name, *args, **kwargs)
    if name.startswith("plugin.") or name.startswith("script."):
        wrap_module(module)
    return module

builtins.__import__ = spy_import

wrap_module()

Iterates over callables

Wraps with decorator:


def wrap(func):
    def traced(*a, **k):
        log_call(func, a, k)
        return func(*a, **k)
    return traced


---

4. Capture Layers

4.1 UI Interceptor

Logs:

Dialog.ok

Dialog.notification

DialogProgress.create/update/close


Stores:

{
  "type": "ui",
  "method": "notification",
  "heading": "Error",
  "message": "Stream not found",
  "addon": "plugin.video.x",
  "stack": [...]
}


---

4.2 DB Spy

Wrap sqlite3.connect:

Cursor.execute()

commit()

close()


Capture:

SQL

params

table names

timing



---

4.3 Network Monitor

Wrap:

requests.get/post

urllib.request.urlopen

xbmcvfs.File reads


Capture:

URL

headers

response size

calling addon



---

4.4 Filesystem Monitor

Wrap:

xbmcvfs.File

shutil.copy

os.remove


Capture:

path

size

source addon



---

5. Call Logger

All events flow into:

{
  "timestamp": "...",
  "addon_id": "...",
  "type": "db|ui|network|fs|call",
  "data": {...},
  "stack": [...]
}

Stored as:

JSONL

Indexed by addon_id + session_id



---

6. Pattern Extractor

Input: Event log timeline
Output: Action graphs

Example extraction:

User click →
  network GET →
  file write →
  db INSERT →
  notification

Converted to:

{
  "action": "download_item",
  "steps": [
    "GET url",
    "save file",
    "INSERT db",
    "notify user"
  ],
  "template": "python code"
}


---

7. Exporter (Multi-format)

Format	Purpose

json	programmatic
ai_handoff	markdown with context
compact	one-line patterns
detailed	full report + code


export(format="ai_handoff")


---

8. Code Injector (Optional)

Generates inline instrumentation snippets to paste into addons.

from fluidsnoop import log
log("favorites.add", item)

Used when:

External hooks insufficient

You need precise state



---

9. Build Phases

Phase	Modules

1	call_logger, ui_interceptor
2	runtime_hook
3	db_spy, network_monitor
4	pattern_extractor
5	exporter
6	code_injector



---

10. What This Solves

Extracts real working flows (not guessed)

Rebuilds favorites, downloads, auth, menus

Learns UI feedback patterns

Works with obfuscated addons

Generates reusable logic blocks
...

**Missing from build:**
- `fs_monitor.py` (filesystem operations)
- JSONL storage format (used JSON)
- `session_id` indexing

**Added to build:**
- Module `__init__.py` for imports
- Full router menu UI
- Export formats already implemented