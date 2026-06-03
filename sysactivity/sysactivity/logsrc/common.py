"""
common.py
=========
Small shared helpers used by every log reader.

The whole app follows ONE simple idea:
    1. Read a log file (or journalctl output) line by line.
    2. Keep only the lines that belong to TODAY.
    3. Pull out the useful piece of each line with a regular expression.
    4. Hand that data to the natural-language layer (nl.py) to turn it
       into a friendly English sentence.

This file only handles steps 1 and 2 (reading + "is this today?").
"""

from __future__ import annotations

import datetime as _dt
import glob
import gzip
from pathlib import Path


# Where our own generated logs live (the HTTP site log, for example).
DATA_DIR = Path.home() / ".local" / "share" / "sysactivity"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def today() -> _dt.date:
    """Return today's calendar date (local time)."""
    return _dt.datetime.now().astimezone().date()


def parse_syslog_timestamp(token: str) -> _dt.datetime | None:
    """
    Ubuntu 24.04 writes ISO-8601 timestamps at the start of every log line,
    e.g.  '2026-06-01T11:04:55.784659+05:30'

    We turn that text into a real datetime object so we can compare dates
    and format a friendly time later. Returns None if the text isn't a date.
    """
    try:
        return _dt.datetime.fromisoformat(token)
    except (ValueError, TypeError):
        return None


def read_lines(path: str | Path) -> list[str]:
    """
    Read a log file safely.

    Logs can contain stray bytes, so we ignore decode errors instead of
    crashing. If the file does not exist or we lack permission, we simply
    return an empty list — the UI then shows "no activity" rather than an
    error, which is exactly what we want during a live demo.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.readlines()
    except (FileNotFoundError, PermissionError):
        return []


def read_log_files(base_path: str | Path) -> list[str]:
    """
    Read a log file AND its rotated older copies.

    Linux rotates logs: today's data is in e.g. /var/log/auth.log, yesterday's
    may be in auth.log.1, and older days are compressed as auth.log.2.gz,
    auth.log.3.gz ... We read all of them so the date-picker can show PAST
    days, not only today. Missing/unreadable files are skipped silently.
    """
    base = str(base_path)
    paths = [base, base + ".1"] + sorted(glob.glob(base + ".*.gz"))
    lines: list[str] = []
    for p in paths:
        if p.endswith(".gz"):
            try:
                with gzip.open(p, "rt", encoding="utf-8", errors="ignore") as fh:
                    lines.extend(fh.readlines())
            except (FileNotFoundError, PermissionError, OSError):
                continue
        else:
            lines.extend(read_lines(p))
    return lines


def line_is_today(line: str, day: _dt.date | None = None) -> _dt.datetime | None:
    """
    Given a raw syslog/auth.log line, return its datetime IF it happened on
    `day` (defaults to today), otherwise None. The timestamp is always the
    first whitespace-separated token on the line.
    """
    if not line:
        return None
    if day is None:
        day = today()
    first_token = line.split(" ", 1)[0]
    ts = parse_syslog_timestamp(first_token)
    if ts is None:
        return None
    if ts.date() == day:
        return ts
    return None
