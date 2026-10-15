#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compatibility entrypoint for `/specialist-headless-finder` SKILL.md (`specialist_finder_tools.py`),
re-exporting all functions and CLI behavior from `specialist_headless_finder_tools.py`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from specialist_headless_finder_tools import (  # noqa: E402,F401
    execute_finder_action,
    finder_get_selection,
    finder_inspect_item,
    finder_mesh_search,
    finder_reveal_path,
    finder_spotlight_search,
    main,
)

if __name__ == "__main__":
    sys.exit(main())
