"""
nl.py  — the "Natural Language" layer (your "nlm")
==================================================
This is the heart of the "simple English for common users" requirement.

There is NO AI model here. Each function takes the raw data from the log
readers and builds plain sentences using fixed templates. This is:
  * fast        (no model to load, instant results)
  * reliable    (it can never hallucinate a wrong fact during the demo)
  * explainable (you can show the company exactly how each sentence is made)

Each builder returns a dict the UI renders:
  {
    "title":   short section heading,
    "headline": one-line summary ("3 SSH logins today"),
    "items":   list of friendly sentences,
    "empty":   True/False,
  }
"""

from __future__ import annotations

import datetime as _dt

from .logsrc import ssh, passwords, devices, http_sites
from .logsrc.common import today


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _when(day: _dt.date) -> str:
    """Word used in headlines: 'today' for today, otherwise the actual date."""
    return "today" if day == today() else f"on {day.strftime('%b %-d, %Y')}"


# ── #1  SSH connections ───────────────────────────────────────────────
def ssh_section(day: _dt.date) -> dict:
    when = _when(day)
    s = ssh.summary(day)
    items = []
    for e in s["events"]:
        if e.success:
            items.append(
                f"At {e.time}, user '{e.user}' logged in remotely over SSH "
                f"from {e.ip} (using a {e.method}).")
        else:
            items.append(
                f"At {e.time}, a remote login over SSH FAILED for '{e.user}' "
                f"from {e.ip}.")

    if s["total"] == 0:
        headline = f"No remote (SSH) connections {when}."
    else:
        bits = [f"{_plural(s['successful'], 'successful remote login')}"]
        if s["failed"]:
            bits.append(f"{_plural(s['failed'], 'failed attempt')}")
        headline = " and ".join(bits) + f" {when}."
        if s["unique_ips"]:
            headline += f" From {_plural(len(s['unique_ips']), 'address')}: " \
                        + ", ".join(s["unique_ips"]) + "."

    return _pack("Remote Connections (SSH)", headline, items)


# ── #2  Password changes ──────────────────────────────────────────────
def password_section(day: _dt.date) -> dict:
    when = _when(day)
    changes = passwords.get_password_changes(day)
    items = []
    for c in changes:
        if c.by:
            items.append(f"At {c.time}, the password for '{c.user}' was changed by '{c.by}'.")
        else:
            items.append(f"At {c.time}, the password for account '{c.user}' was changed.")
    headline = (f"No passwords were changed {when}." if not changes
                else f"{_plural(len(changes), 'password change')} {when}.")
    return _pack("Password Changes", headline, items)


# ── #3  External devices ──────────────────────────────────────────────
def devices_section(day: _dt.date) -> dict:
    when = _when(day)
    devs = devices.get_devices(day)
    items = []
    for d in devs:
        brand = (d.manufacturer + " ") if d.manufacturer else ""
        when_dev = f"at {d.time}" if d.time else "then"
        line = f"{brand}{d.name} was connected {when_dev}."
        extra = []
        if d.size:
            extra.append(f"storage size {d.size}")
        if d.serial and d.serial not in ("0", ""):
            extra.append(f"serial {d.serial}")
        if extra:
            line += " (" + ", ".join(extra) + ")"
        if d.warning:
            line += f"  ⚠ This device {d.warning}."
        items.append(line)
    headline = (f"No external devices were connected {when}." if not devs
                else f"{_plural(len(devs), 'external device')} connected {when}.")
    return _pack("External Devices", headline, items)


# ── #4  Insecure HTTP sites ───────────────────────────────────────────
def http_section(day: _dt.date) -> dict:
    when = _when(day)
    s = http_sites.summary(day)
    items = []
    for v in s["visits"]:
        items.append(
            f"At {v.time}, visited {v.url} — this site is INSECURE (plain HTTP, "
            f"not encrypted).")
    if s["total"] == 0:
        headline = f"No insecure (HTTP) websites were visited {when}."
    else:
        headline = (f"{_plural(s['total'], 'visit')} to "
                    f"{_plural(len(s['unique_sites']), 'insecure website')} {when}.")
    return _pack("Insecure Websites (HTTP)", headline, items)


def _pack(title: str, headline: str, items: list[str]) -> dict:
    return {"title": title, "headline": headline, "items": items,
            "empty": len(items) == 0}


def all_sections(day: _dt.date | None = None) -> list[dict]:
    """The four activities, in the order the TL asked for them.

    `day` selects which date to report on (defaults to today). The UI passes
    the date chosen in the calendar picker.
    """
    if day is None:
        day = today()
    return [ssh_section(day), password_section(day),
            devices_section(day), http_section(day)]
