"""pytest configuration for the ai-service.

Adds the ai-service directory to sys.path so test files can do bare
imports like `from chunker import ...` without each test file having to
mutate sys.path itself. Equivalent to setting `pythonpath = ["."]` in
pytest config, but plays nicer with editors that don't read pytest.ini.
"""

from __future__ import annotations

import sys
from pathlib import Path

_AI_SERVICE = Path(__file__).resolve().parent
if str(_AI_SERVICE) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICE))
