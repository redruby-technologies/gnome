#!/usr/bin/env python3
"""
run.py — start the System Activity Monitor (top-bar icon + window).

Usage:
    python3 run.py

Self-healing note:
    If this is launched from a snap-based terminal (e.g. snap VS Code), the
    environment contains GTK_PATH / GIO_MODULE_DIR / LD_LIBRARY_PATH values
    that point inside the snap and break GTK. We detect those, strip them,
    and re-launch ourselves in a clean environment BEFORE importing GTK.
"""

import os
import sys


def _scrub_snap_env_and_relaunch():
    """Remove env vars pointing into a snap and re-exec once if needed."""
    if os.environ.get("_SYSACT_CLEANED") == "1":
        return  # already relaunched; don't loop
    polluted = [k for k, v in os.environ.items()
                if isinstance(v, str) and "/snap/" in v
                and k not in ("PATH", "XDG_DATA_DIRS")]
    # These specifically break GTK if they point into a snap.
    for key in ("GTK_PATH", "GTK_EXE_PREFIX", "GIO_MODULE_DIR",
                "GDK_PIXBUF_MODULE_FILE", "GDK_PIXBUF_MODULEDIR",
                "GSETTINGS_SCHEMA_DIR", "LOCPATH", "LD_LIBRARY_PATH"):
        if key in os.environ and "/snap/" in os.environ[key]:
            polluted.append(key)
    if not polluted:
        return
    clean = dict(os.environ)
    for key in set(polluted):
        clean.pop(key, None)
    clean["_SYSACT_CLEANED"] = "1"
    os.execve(sys.executable, [sys.executable] + sys.argv, clean)


_scrub_snap_env_and_relaunch()

from sysactivity.app import main  # noqa: E402  (imported after env scrub)

if __name__ == "__main__":
    main()
