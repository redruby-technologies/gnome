"""
http_sites.py
=============
Activity #4 — INSECURE (HTTP) websites visited today.

IMPORTANT SECURITY FACT (good to say in the demo):
  HTTPS traffic is encrypted, so the site name is NOT visible to anyone on
  the network. Only plain HTTP (port 80) leaks the website name in clear
  text. That is exactly why we ONLY track HTTP here — those are the visits
  worth warning a user about, because they are unencrypted and unsafe.

This module simply READS a log file (per the chosen design). The log file is
produced by the optional helper `http_logger.py`, which sniffs port-80
traffic and appends one line per visit in this format:

  2026-06-01T14:25:10+05:30 \t neverssl.com \t http://neverssl.com/

If the log file doesn't exist yet, we return nothing and the UI shows a
friendly "no insecure sites today" message.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from .common import DATA_DIR, parse_syslog_timestamp, today

HTTP_LOG = DATA_DIR / "http_sites.log"

# One web page makes MANY HTTP requests (page + images + css + favicon +
# redirects), so the sniffer logs dozens of lines for a single visit. We treat
# requests to the SAME site that arrive within this gap as ONE visit, so two
# separate browser navigations show as 2 visits — not 53.
VISIT_GAP = _dt.timedelta(seconds=15)


@dataclass
class HttpVisit:
    host: str
    url: str
    time: str


def get_http_visits(day: _dt.date | None = None) -> list[HttpVisit]:
    """Read the HTTP log for `day` (defaults to today) and collapse the burst
    of sub-requests into real visits (see VISIT_GAP). If the log file does not
    exist yet, we simply return nothing."""
    if day is None:
        day = today()
    try:
        lines = HTTP_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
    except FileNotFoundError:
        return []

    # 1) Parse every logged request for the chosen day into (datetime, host, url).
    raw_hits: list[tuple[_dt.datetime, str, str]] = []
    for raw in lines:
        # Our HTTP log is TAB-separated:  TIMESTAMP \t HOST \t URL
        parts = raw.rstrip("\n").split("\t")
        if len(parts) < 2:
            continue
        ts = parse_syslog_timestamp(parts[0].strip())
        if ts is None or ts.date() != day:
            continue
        host = parts[1].strip()
        url = parts[2].strip() if len(parts) > 2 else f"http://{host}"
        raw_hits.append((ts, host, url))

    # 2) Collapse the burst of sub-requests into real "visits".
    raw_hits.sort(key=lambda h: h[0])
    last_seen: dict[str, _dt.datetime] = {}
    visits: list[HttpVisit] = []
    for ts, host, url in raw_hits:
        prev = last_seen.get(host)
        last_seen[host] = ts                 # always extend the session window
        if prev is not None and (ts - prev) <= VISIT_GAP:
            continue                         # same visit → skip this sub-request
        visits.append(HttpVisit(host=host, url=url, time=ts.strftime("%-I:%M %p")))
    return visits


def summary(day: _dt.date | None = None) -> dict:
    visits = get_http_visits(day)
    return {
        "visits": visits,
        "total": len(visits),
        "unique_sites": sorted({v.host for v in visits}),
    }
