"""Import the plugin directory as a package so `from .search1api import ...`
takes the package path (mirroring Hermes plugin discovery)."""
from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent
ALIAS = "hermes_search1api_pkg"

if ALIAS not in sys.modules:
    import types

    pkg = types.ModuleType(ALIAS)
    pkg.__path__ = [str(PLUGIN_DIR)]  # type: ignore[attr-defined]
    pkg.__file__ = str(PLUGIN_DIR / "__init__.py")
    sys.modules[ALIAS] = pkg
    code = (PLUGIN_DIR / "__init__.py").read_text()
    exec(compile(code, str(PLUGIN_DIR / "__init__.py"), "exec"), pkg.__dict__)
