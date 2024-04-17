# Configuration file for the Sphinx documentation builder.

import os
import sys
from pathlib import Path
from typing import Optional, Type, TypeVar

import tomlkit  # type: ignore[import]

sys.path.insert(0, os.path.abspath("../../sengledwifipy"))

# This assumes that we have the full project root above, containing pyproject.toml
_root = Path(__file__).parent.parent.parent.absolute()
_toml = tomlkit.loads((_root / "pyproject.toml").read_text(encoding="utf8"))

T = TypeVar("T")

def find(key: str, default: Optional[T] = None, as_type: type[T] = str) -> Optional[T]:
    """
    Gets a value from pyproject.toml, or a default.

    Original source: https://github.com/dmyersturnbull/tyrannosaurus
    Copyright 2020–2021 Douglas Myers-Turnbull
    SPDX-License-Identifier: Apache-2.0

    Args:
        key: A period-delimited TOML key; e.g. ``tools.poetry.name``
        default: Default value if any node in the key is not found
        as_type: Convert non-``None`` values to this type before returning

    Returns:
        The value converted to ``as_type``, or ``default`` if it was not found
    """
    at = _toml
    for k in key.split("."):
        at = at.get(k)
        if at is None:
            return default
    return as_type(at)

# -- Project information -----------------------------------------------------

language = "en"
project = find("tool.poetry.name")
version = find("tool.poetry.version")
release = version
copyright = f"{project} v{release}"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "myst_parser"
]

# -- Options for HTML output -------------------------------------------------

html_theme = "furo"

html_theme_options = {
    "globaltoc_collapse": False,
    "globaltoc_includehidden": False,
    "globaltoc_maxdepth": 2,
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/cpadil/sengledwifipy",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            """,
            "class": "",
        },
    ],
}
html_show_copyright = True
html_title = f"SengledWifiPy \n v{release}"
html_last_updated_fmt = "%Y-%m-%d"

# -- Other Options  -------------------------------------------------

# general
add_module_names = False # whether module names are prepended to all object names
autodoc_member_order = "bysource"
autodoc_class_signature = "separated"

today_fmt = "%Y-%m-%d"
