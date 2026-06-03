"""
passwords.py
============
Activity #2 — PASSWORD CHANGES today.

When someone changes a password on Linux, PAM writes a line to
/var/log/auth.log such as:

  passwd[12345]: pam_unix(passwd:chauthtok): password changed for ubuntu

We also catch new-account password setup and admin-forced changes:

  chpasswd[...]: pam_unix(chpasswd:chauthtok): password changed for bob
  passwd[...]: password for 'bob' changed by 'root'
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass

from .common import line_is_today, read_log_files

AUTH_LOG = "/var/log/auth.log"


@dataclass
class PasswordChange:
    user: str
    time: str
    by: str = ""   # who made the change, if the log says so


_CHANGED = re.compile(r"password changed for (?P<user>\S+)")
_CHANGED_BY = re.compile(r"password for [\"']?(?P<user>[^\"' ]+)[\"']? changed by [\"']?(?P<by>[^\"' ]+)")


def get_password_changes(day: _dt.date | None = None) -> list[PasswordChange]:
    """Parse the password changes for `day` (defaults to today) from the logs
    (auth.log + rotated copies)."""
    changes: list[PasswordChange] = []
    for raw in read_log_files(AUTH_LOG):
        if "passwd" not in raw and "chpasswd" not in raw and "chauthtok" not in raw:
            continue
        ts = line_is_today(raw, day)
        if ts is None:
            continue
        time = ts.strftime("%-I:%M %p")

        m = _CHANGED_BY.search(raw)
        if m:
            changes.append(PasswordChange(
                user=m.group("user"), time=time, by=m.group("by")))
            continue

        m = _CHANGED.search(raw)
        if m:
            changes.append(PasswordChange(user=m.group("user"), time=time))
    return changes
