# Configuration file for the Sphinx documentation builder.

import os
import sys
from pathlib import Path
from typing import Optional, Type, TypeVar

import tomlkit  # type: ignore[import]

sys.path.insert(0, os.path.abspath("../../sengledwifipy"))
# sys.path.insert(0, os.path.abspath('.'))

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

html_theme = "sphinx_book_theme"

html_theme_options = {
    "repository_url":"https://github.com/cpadil/sengledwifipy",
    "use_repository_button": True, 
    "use_download_button" : False,
    "use_fullscreen_button": False,
    "show_toc_level": 1, # secondary toc
    "toc_title": "In this page:", # secondary toc
    "home_page_in_toc": True,
    "show_navbar_depth": 2,
    "max_navbar_depth": 3,
    "collapse_navbar": False,
    "show_nav_level": 2
}
html_show_copyright = True
html_title = f"SengledWifiPy \n v{release}"
html_last_updated_fmt = "%Y-%m-%d"

# -- Other Options  -------------------------------------------------

#general
add_module_names = False #whether module names are prepended to all object names
autodoc_member_order = "bysource"


today_fmt = "%Y-%m-%d"
