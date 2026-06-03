"""
devices.py
==========
Activity #3 — EXTERNAL DEVICES connected today (present + earlier today).

This module is adapted from the user's original `parse_devices()` script.
Original idea (kept): walk the kernel log, group the lines that describe ONE
device (Product / Manufacturer / SerialNumber / size), and flag a device that
was "not properly unmounted" (unsafe removal).

What changed vs the original:
  * We read kernel logs with `journalctl -k` (no sudo needed) and fall back to
    `dmesg`, then to /var/log/syslog — whichever works on the machine.
  * We capture EVERY USB device (mouse, camera, pen-drive...), not only disks,
    because the demo asks for "all external devices connected today".
  * We attach the time each device appeared so the UI can say "at 11:04 AM".
"""

from __future__ import annotations

import datetime as _dt
import re
import subprocess
from dataclasses import dataclass, field

from .common import line_is_today, read_log_files, today


@dataclass
class Device:
    name: str = "Unknown device"
    manufacturer: str = ""
    serial: str = ""
    size: str = ""
    time: str = ""              # friendly "11:04 AM"
    vendor_product: str = ""    # e.g. 0461:574a (useful detail for techies)
    warning: str = ""           # e.g. "was not safely removed last time"


# A kernel "usb 3-4: ..." line. We use the bus id (3-4) to group lines.
_USB_ID = re.compile(r"usb (\d+-[\d.]+):")


def _kernel_lines(day: _dt.date) -> list[str]:
    """
    Get the kernel log lines for `day`, trying the no-sudo source first.
    journalctl -k -o short-iso gives lines whose timestamp we can read with
    the same helper used everywhere else. We bound it to the chosen day with
    --since/--until so the date-picker can show past days too.
    """
    since = day.strftime("%Y-%m-%d 00:00:00")
    until = (day + _dt.timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")

    # 1) journalctl, kernel messages, bounded to the chosen day.
    #    We match _TRANSPORT=kernel instead of "-k", because "-k" only shows the
    #    CURRENT boot — and a past day is usually a previous boot. Matching the
    #    kernel transport pulls kernel lines across all boots the journal keeps.
    try:
        out = subprocess.run(
            ["journalctl", "--since", since, "--until", until,
             "-o", "short-iso", "--no-pager", "_TRANSPORT=kernel"],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode == 0 and out.stdout.strip():
            return _normalise_journal(out.stdout.splitlines())
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # 2) /var/log/syslog (+ rotated copies) carry kernel lines with ISO times.
    syslog = [l for l in read_log_files("/var/log/syslog") if "kernel:" in l]
    if syslog:
        return syslog

    # 3) Last resort: plain dmesg (no per-line wall-clock date).
    try:
        out = subprocess.run(["dmesg"], capture_output=True, text=True, timeout=10)
        return out.stdout.splitlines()
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def _normalise_journal(lines: list[str]) -> list[str]:
    """
    journalctl 'short-iso' prints e.g.
        2026-06-01T11:04:55+0530 ubuntu kernel: usb 3-4: Product: ...
    Our timestamp parser wants a colon in the timezone (+05:30). Insert it so
    line_is_today() can read it.
    """
    fixed = []
    tz = re.compile(r"^(\S+T\d\d:\d\d:\d\d)([+-]\d{2})(\d{2})")
    for l in lines:
        fixed.append(tz.sub(r"\1\2:\3", l, count=1))
    return fixed


def get_devices(day: _dt.date | None = None) -> list[Device]:
    """
    Return the external devices connected on `day` (defaults to today).

    The grouping logic mirrors the user's original script: a "New USB device"
    line starts a fresh device record; following Product/Manufacturer/Serial
    lines fill it in; we finish a record when the next device starts.

    Each physical plug-in is its own record: if you connect the SAME device at
    11:05 AM and again at 4:00 PM, both appear, because each plug-in writes a
    fresh "new USB device" line with its own time (the time is part of the
    de-duplication key in _commit).
    """
    if day is None:
        day = today()
    lines = _kernel_lines(day)
    devices: list[Device] = []
    current: Device | None = None
    seen_keys: set[tuple] = set()

    for raw in lines:
        ts = line_is_today(raw, day)
        low = raw.lower()

        # Start of a new device block.
        if "new usb device found" in low or "new high-speed usb device" in low \
                or "new full-speed usb device" in low or "new low-speed usb device" in low \
                or "new superspeed usb device" in low:
            # Save the previous one before starting a new block.
            if current and current.name != "Unknown device":
                _commit(current, devices, seen_keys)
            current = Device()
            if ts:
                current.time = _fmt_time(ts)
            m = re.search(r"idVendor=(\w+).*?idProduct=(\w+)", raw)
            if m:
                current.vendor_product = f"{m.group(1)}:{m.group(2)}"

        if current is None:
            continue

        if "product:" in low:
            current.name = raw.split("Product:", 1)[-1].strip()
        elif "manufacturer:" in low:
            current.manufacturer = raw.split("Manufacturer:", 1)[-1].strip()
        elif "serialnumber:" in low and "strings:" not in low:
            current.serial = raw.split("SerialNumber:", 1)[-1].strip()
        elif "logical blocks" in low:
            # e.g. "... 30031872 512-byte logical blocks: (15.4 GB/14.3 GiB)"
            m = re.search(r"\(([^)]+)\)", raw)
            if m:
                current.size = m.group(1).split("/")[0].strip()
        elif "not properly unmounted" in low and devices:
            devices[-1].warning = "was not safely removed last time"

    if current and current.name != "Unknown device":
        _commit(current, devices, seen_keys)

    return devices


# Built-in USB plumbing we should NOT show as "external devices".
# 1d6b = Linux Foundation root hubs; "host controller"/"root hub" are internal.
_INTERNAL_VENDORS = {"1d6b"}
_INTERNAL_WORDS = ("host controller", "root hub")


def _is_internal(dev: Device) -> bool:
    name = dev.name.lower()
    if any(w in name for w in _INTERNAL_WORDS):
        return True
    vendor = dev.vendor_product.split(":", 1)[0].lower()
    return vendor in _INTERNAL_VENDORS


def _commit(dev: Device, devices: list[Device], seen: set) -> None:
    """Add a device, skipping internal USB hubs and exact duplicates.

    The time is part of the key, so the SAME device connected at two different
    times shows up as two records — but enumeration retries within the same
    minute (same time string) still collapse into one.
    """
    if _is_internal(dev):
        return
    key = (dev.name, dev.serial, dev.vendor_product, dev.time)
    if key in seen:
        return
    seen.add(key)
    devices.append(dev)


def _fmt_time(ts) -> str:
    return ts.strftime("%-I:%M %p")
