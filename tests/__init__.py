"""Test package for the repository's Python tooling.

The scripts are hyphenated executables rather than importable modules, so every
test loads them through an explicit file-location import instead of a package
import. `load_script` is that one place.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent


def load_script(filename: str, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "scripts" / filename)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load scripts/{filename}")
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves field types through sys.modules, so the module has to
    # be registered before exec_module rather than after.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
