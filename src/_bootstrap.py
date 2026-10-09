"""Make the repo's vendored third-party libraries importable.

This repo keeps numpy / matplotlib under ``pylibs/`` at the repository root so
that nothing has to be pip-installed. Importing this module first (before
numpy) appends that folder to ``sys.path``.

    import _bootstrap  # noqa: F401  -- must come before `import numpy`
"""

import sys
from pathlib import Path

_LIBS = Path(__file__).resolve().parents[3] / "pylibs"
if _LIBS.is_dir() and str(_LIBS) not in sys.path:
    sys.path.append(str(_LIBS))
