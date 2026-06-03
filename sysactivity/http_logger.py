#!/usr/bin/env python3
"""
http_logger.py  — OPTIONAL background helper for Activity #4.
=============================================================
This is the piece that PRODUCES the HTTP log file that the app READS
(~/.local/share/sysactivity/http_sites.log).

It sniffs network traffic on port 80 (plain HTTP) and records the website
name from each request's "Host:" header. HTTPS is encrypted, so it never
appears here — which is exactly the point: we only flag the insecure visits.

Run it (needs root, because sniffing the network card requires privilege):
    sudo python3 http_logger.py            # auto-detect interface
    sudo python3 http_logger.py -i wlp0s20f3

It uses scapy. Install once:  sudo apt install python3-scapy
(If scapy isn't available, the app still works — it just shows no HTTP sites,
or whatever the demo seed file contains.)

NOTE for the demo: live sniffing needs you to actually visit an http:// site
while this is running (try http://neverssl.com). If you'd rather not run a
live sniffer in front of the company, use seed_demo.py to pre-fill realistic
sample visits instead.
"""

from __future__ import annotations

import argparse
import datetime
import os
import pwd
import sys
from pathlib import Path


def _real_home() -> Path:
    """
    Home of the human who launched us — NOT root's home.

    We are run with `sudo`, so `Path.home()` would be /root and the log would
    land in /root/.local/... where the GTK app (running as the normal user)
    can never read it. `sudo` sets SUDO_USER to the original username, so we
    resolve THAT user's home instead. Without sudo we just use Path.home().
    """
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        try:
            return Path(pwd.getpwnam(sudo_user).pw_dir)
        except KeyError:
            pass
    return Path.home()


LOG = _real_home() / ".local" / "share" / "sysactivity" / "http_sites.log"
LOG.parent.mkdir(parents=True, exist_ok=True)


def _append(host: str, url: str) -> None:
    ts = datetime.datetime.now().astimezone().isoformat()
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(f"{ts}\t{host}\t{url}\n")
    print(f"[http] {host}  ->  logged")


def main() -> int:
    ap = argparse.ArgumentParser(description="Log insecure HTTP site visits.")
    ap.add_argument("-i", "--iface", default=None,
                    help="network interface (default: scapy picks one)")
    ap.add_argument("--logfile", default=None,
                    help="where to write the log (used by the systemd service, "
                         "so a root service writes to the user's folder, not /root)")
    args = ap.parse_args()

    if args.logfile:
        global LOG
        LOG = Path(args.logfile)
        LOG.parent.mkdir(parents=True, exist_ok=True)

    try:
        from scapy.all import sniff, TCP, Raw  # type: ignore
    except ImportError:
        print("scapy is not installed. Run:  sudo apt install python3-scapy",
              file=sys.stderr)
        return 1

    if os.geteuid() != 0:
        print("This needs root to sniff the network. Run with: sudo python3 http_logger.py",
              file=sys.stderr)
        return 1

    print(f"Listening for insecure HTTP visits... logging to {LOG}")
    print("Visit an http:// site (e.g. http://neverssl.com) to see it appear.")
    print("Press Ctrl-C to stop.\n")

    def handle(pkt):
        if not (pkt.haslayer(TCP) and pkt.haslayer(Raw)):
            return
        try:
            payload = bytes(pkt[Raw].load).decode("latin-1", "ignore")
        except Exception:
            return
        if not payload.startswith(("GET ", "POST ", "HEAD ", "PUT ")):
            return
        host = ""
        path = "/"
        for line in payload.split("\r\n"):
            if line.lower().startswith("host:"):
                host = line.split(":", 1)[1].strip()
            elif line.startswith(("GET ", "POST ", "HEAD ", "PUT ")):
                parts = line.split(" ")
                if len(parts) > 1:
                    path = parts[1]
        if host:
            _append(host, f"http://{host}{path}")

    try:
        sniff(filter="tcp port 80", prn=handle, store=False, iface=args.iface)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
