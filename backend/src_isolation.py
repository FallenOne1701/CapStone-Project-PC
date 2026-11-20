"""Process-wide lock for any ``sys.modules['src.*']`` swap.

FAQ backend and Support Deck (and Pulse) all use a top-level ``src`` package.
Concurrent swaps without this lock corrupt imports (e.g. ``No module named
'src.ingest'``) and take down ``/health`` / ``/api/ask``.
"""

from __future__ import annotations

import threading

SRC_SWAP_LOCK = threading.RLock()
