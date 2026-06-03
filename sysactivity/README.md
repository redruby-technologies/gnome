# System Activity Monitor

A small Linux desktop app that puts an icon in the **top bar** (like the
wifi/volume icons). Click it → a window opens showing **today's system
activity** in **plain, simple English** that a non-technical user can
understand.

It reports the four activities requested:

1. **Remote Connections (SSH)** — who logged in remotely, from where, how many times
2. **Password Changes** — which accounts had their password changed, and when
3. **External Devices** — USB / external devices connected today (with size & serial)
4. **Insecure Websites (HTTP)** — plain-HTTP (unencrypted) sites visited today

There is **no AI model**. Every sentence is built from fixed templates
("nlm" = natural-language method), so it is fast, reliable, and explainable.

---

## 1. Install (one-time, ~30 seconds)

```bash
# The top-bar icon needs this library (this is the ONLY step needing sudo):
sudo apt update
sudo apt install -y gir1.2-ayatanaappindicator3-0.1 gir1.2-gtk-3.0

# (Optional) for live HTTP sniffing in activity #4:
sudo apt install -y python3-scapy
```

> Ubuntu 24.04 already shows AppIndicator icons in the top bar via its
> built-in "Ubuntu AppIndicators" extension, so nothing else is needed.

## 2. Run

```bash
cd ~/sysactivity
python3 run.py
```

A shield icon appears in the top bar. Click it → **"Open Today's Activity"**.

> `run.py` auto-cleans the snap environment, so it works even when started
> from a snap terminal (like snap VS Code).

---

## 3. How it works (top to bottom — for your presentation)

```
   TOP BAR ICON  (sysactivity/app.py, using AppIndicator)
        │  click → "Open Today's Activity"
        ▼
   WINDOW        (sysactivity/ui.py, GTK3 — one card per activity)
        │  asks for sentences
        ▼
   NL LAYER      (sysactivity/nl.py — turns data into simple English)
        │  asks for data
        ▼
   LOG READERS   (sysactivity/logsrc/*.py — read & filter today's logs)
        │  read raw lines
        ▼
   LINUX LOGS    (/var/log/auth.log, journalctl -k, our HTTP log file)
```

**The pipeline for every activity is the same 4 steps:**
1. Read a log source.
2. Keep only **today's** lines (`common.line_is_today`).
3. Pull out the useful fields with a regular expression.
4. Format a plain-English sentence (`nl.py`).

### Where each activity's data comes from

| # | Activity | Source | Key file |
|---|----------|--------|----------|
| 1 | SSH connections | `/var/log/auth.log` (`Accepted`/`Failed ... for ... from ...`) | `logsrc/ssh.py` |
| 2 | Password changes | `/var/log/auth.log` (`password changed for ...`) | `logsrc/passwords.py` |
| 3 | External devices | `journalctl -k` / syslog (USB `Product:`/`Manufacturer:`/serial) | `logsrc/devices.py` |
| 4 | Insecure HTTP sites | a log file we generate (`~/.local/share/sysactivity/http_sites.log`) | `logsrc/http_sites.py` |

> **#3 is adapted from your original `parse_devices()` script** — same idea of
> grouping `Product`/`Manufacturer`/`SerialNumber`/size lines and flagging
> "not safely removed", but reading via `journalctl -k` so it needs **no sudo**,
> and filtering out internal USB hubs so only *real* plugged-in devices show.

> **Why only HTTP, not HTTPS (good to say in the demo):** HTTPS is encrypted,
> so the website name is invisible on the network. Only plain HTTP leaks the
> site name in clear text — those are exactly the unsafe visits worth warning
> a user about.

---

## 4. Make the demo show real, live data (recommended)

The logs may be empty on a fresh machine. Trigger real events live — it's
very convincing:

```bash
# (1) Real SSH connection — log in to your own machine:
ssh localhost            # type 'yes' then your password, then 'exit'

# (2) Real password change (you can keep the same password):
passwd                   # follow the prompts

# (3) Real external device — just plug in a USB pen-drive.

# (4) Real insecure website — run the sniffer in one terminal:
sudo python3 http_logger.py
#    then in a browser visit:  http://neverssl.com
```

Then click the top-bar icon → **Refresh** → watch the new activity appear.

---

## 5. Project layout

```
sysactivity/
├── run.py              ← start here (top-bar icon + window)
├── install.sh          ← auto-start the GUI (+ optional HTTP sniffer) via systemd
├── http_logger.py      ← optional: live HTTP sniffer (writes the HTTP log)
├── README.md           ← this file
└── sysactivity/
    ├── app.py          ← top-bar AppIndicator icon + menu
    ├── ui.py           ← the GTK window (4 cards + date picker + search)
    ├── nl.py           ← natural-language sentence builder (the "nlm")
    └── logsrc/
        ├── common.py       ← shared: read files (+ rotated .gz), "is this day?"
        ├── ssh.py          ← #1 SSH connections
        ├── passwords.py    ← #2 password changes
        ├── devices.py      ← #3 external devices (from your script)
        └── http_sites.py   ← #4 insecure HTTP sites
```

## 6. Common questions (for the Q&A)

- **Does it need root?** No, for reading SSH/password/device logs — the user
  just needs to be in the `adm` group (default for the main Ubuntu user).
  Only the *optional* live HTTP sniffer needs root, because sniffing the
  network card is privileged.
- **Does it slow the computer down?** No. It only reads logs when you open
  or refresh the window. Nothing runs in the background (except the optional
  HTTP sniffer, if you choose to run it).
- **Could it work on other Linux systems?** Yes — it reads standard Linux
  logs. Paths are standard on Debian/Ubuntu; other distros may use
  `journalctl` for everything, which we already support for devices.
- **Privacy?** Everything stays on the machine. Nothing is sent anywhere.
```
