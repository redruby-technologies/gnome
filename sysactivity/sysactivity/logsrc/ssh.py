"""
ssh.py
======
Activity #1 — SSH connections today, with a count.

We read /var/log/auth.log. The lines that matter look like:

  Accepted password for ubuntu from 192.168.1.5 port 54321 ssh2
  Accepted publickey for ubuntu from 10.0.0.9 port 41122 ssh2
  Failed password for invalid user admin from 1.2.3.4 port 5040 ssh2
  Connection closed by 192.168.1.5 port 54321

From each we pull WHO, FROM WHERE, HOW (password / key) and WHEN.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass

from .common import line_is_today, read_log_files

AUTH_LOG = "/var/log/auth.log"


@dataclass
class SshEvent:
    success: bool
    user: str
    ip: str
    method: str   # "password" or "key"
    time: str     # "2:30 PM"


_ACCEPTED = re.compile(
    r"Accepted (?P<method>\w+) for (?P<user>\S+) from (?P<ip>\S+)")
_FAILED = re.compile(
    r"Failed (?P<method>\w+) for (?:invalid user )?(?P<user>\S+) from (?P<ip>\S+)")


def get_ssh_events(day: _dt.date | None = None) -> list[SshEvent]:
    """Parse the SSH events for `day` (defaults to today) straight from the
    logs. We read /var/log/auth.log and its rotated copies, so recent past
    days work too; older days that the OS already deleted simply show empty."""
    events: list[SshEvent] = []
    for raw in read_log_files(AUTH_LOG):
        if "sshd" not in raw:
            continue
        ts = line_is_today(raw, day)
        if ts is None:
            continue
        time = ts.strftime("%-I:%M %p")

        m = _ACCEPTED.search(raw)
        if m:
            events.append(SshEvent(
                success=True, user=m.group("user"), ip=m.group("ip"),
                method=_method(m.group("method")), time=time))
            continue

        m = _FAILED.search(raw)
        if m:
            events.append(SshEvent(
                success=False, user=m.group("user"), ip=m.group("ip"),
                method=_method(m.group("method")), time=time))
    return events


def _method(word: str) -> str:
    return "key" if "key" in word.lower() else "password"


def summary(day: _dt.date | None = None) -> dict:
    """Pre-compute the counts the UI needs for the chosen day."""
    events = get_ssh_events(day)
    ok = [e for e in events if e.success]
    bad = [e for e in events if not e.success]
    return {
        "events": events,
        "total": len(events),
        "successful": len(ok),
        "failed": len(bad),
        "unique_ips": sorted({e.ip for e in ok}),
    }
