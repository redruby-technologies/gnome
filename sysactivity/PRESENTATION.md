# System Activity Monitor — One-Page Cheat Sheet

*(For explaining the project in the meeting.)*

---

## 1. What it is (the pitch)

> A small **Python desktop app**. It puts a shield icon in the **top bar**
> (next to wifi/volume). Click it → a window opens showing **today's
> security activity in plain English**. It works by **reading the operating
> system's own log files** — no AI, no database, no web server.

It reports 4 things that happened **today**:
1. **Remote logins (SSH)** — who logged in from another machine
2. **Password changes** — which accounts changed their password
3. **External devices** — USB devices plugged in
4. **Insecure HTTP sites** — unencrypted websites visited

---

## 2. Is it a web framework? (No.)

- **NOT** FastAPI, **NOT** Django, **NOT** Flask. Those are *web* frameworks
  (server + port + database). This app has none of that.
- It is a **plain Python desktop program** using:
  - **GTK 3** — the toolkit that draws the window, buttons and cards.
  - **AppIndicator** — the library that shows the icon in the top bar.
- No server, no port, no database. Just Python reading log files on demand.

---

## 3. How the top-bar icon works (the SIMPLE version)

Think of GNOME (the Ubuntu desktop) as a **receptionist** who controls the
front desk (the top bar). **Your app cannot place an icon there itself.**

1. Your app **announces** itself: *"I want to show an icon — here is my
   picture (a shield) and my menu."*
2. That announcement travels over **D-Bus** — a built-in Linux messaging
   channel that lets programs talk to each other (like an internal intercom).
3. GNOME has a listener (the **"AppIndicators" extension**) that hears the
   announcement and **places your icon on the top bar** for you.
4. When you **click**, GNOME shows your menu. Clicking *"Open Today's
   Activity"* calls back into your Python code, which opens the GTK window.

> **One-liner:** "We announce a tray icon over D-Bus using AppIndicator;
> GNOME's AppIndicator extension draws it in the top bar. The window itself
> is plain GTK 3."

**Fallback:** if the AppIndicator library is missing, the app skips the icon
and **opens the window directly** — so a demo never crashes.

---

## 4. Where each activity's data comes from

| # | Activity | Source | How we read it |
|---|----------|--------|----------------|
| 1 | SSH logins | `/var/log/auth.log` | Read the file; regex for `Accepted/Failed ... for <user> from <ip>` |
| 2 | Password changes | `/var/log/auth.log` | Read the file; regex for `password changed for <user>` (written by PAM) |
| 3 | External devices | Kernel log via **`journalctl -k`** (fallback: `/var/log/syslog`, then `dmesg`) | Run the command; group `Product:`/`Manufacturer:`/`SerialNumber:`/size lines per USB device |
| 4 | Insecure HTTP | **Live network traffic** (scapy) | A helper sniffs TCP port 80, reads the `Host:` header, writes a log file; the app reads that file |

**Key point about #4:** Linux does **not** log websites you visit (unlike
SSH/passwords/devices, which the OS logs automatically). So HTTP must be
**captured live from the network** with `scapy`. Only `http://` (unencrypted)
is visible; `https://` is encrypted and invisible — which is the whole point:
we only flag the *unsafe* visits.

---

## 5. Project structure (layered, like a backend app)

```
PRESENTATION LAYER
  run.py               → entry point (cleans snap env, then starts the app)
  sysactivity/app.py   → top-bar icon + menu  (wires user clicks)
  sysactivity/ui.py    → GTK window with 4 cards  (the "view" — just renders)

SERVICE / FORMATTING LAYER
  sysactivity/nl.py    → turns raw data into plain-English sentences
                         (fixed templates — no AI; like a response formatter)

DATA-ACCESS LAYER  (logsrc/ — one "repository" per source, read ON DEMAND)
  logsrc/common.py     → shared: read files (+ rotated .gz), "is this day?"
  logsrc/ssh.py        → SSH events       → returns SshEvent objects
  logsrc/passwords.py  → password changes → returns PasswordChange objects
  logsrc/devices.py    → USB devices      → returns Device objects
  logsrc/http_sites.py → HTTP log file    → returns HttpVisit objects

HELPER SCRIPTS / SETUP
  http_logger.py  → the scapy sniffer that PRODUCES the HTTP log (needs sudo)
  seed_demo.py    → fills sample HTTP data for a demo
  install.sh      → auto-starts the GUI (user) + HTTP sniffer (system)
```

**Design highlights:**
- Each `logsrc/*.py` is like a **repository**: knows one source, returns
  **typed objects** (`SshEvent`, `PasswordChange`, `Device`, `HttpVisit`).
- `nl.py` = **service/formatting layer**: objects → sentences.
- `ui.py` = **dumb view**: just displays what `nl.py` returns.
- To add a 5th activity: one new file in `logsrc/` + one function in `nl.py`.

---

## 6. Runtime flow (a tiny ETL, runs on each open/Refresh)

```
 click icon / Refresh
        ↓
 ui.reload() ──► nl.all_sections()
        ↓              ↓ asks each repository in logsrc/
        ↓        1. EXTRACT  → read log file / run journalctl
        ↓        2. FILTER   → keep only TODAY's lines
        ↓        3. TRANSFORM→ regex → typed object
        ↓              ↓
 nl.py:  4. FORMAT → object → plain-English sentence (template)
        ↓
 ui.py renders one card per activity
```

- **On-demand & read-only:** it reads logs only when you open/refresh. Nothing
  runs in the background (except the optional sniffer) → zero slowdown.
- **Fail-safe:** if a log is missing/unreadable, that card shows "Nothing to
  report" instead of crashing.

---

## 7. Does systemd make it "run all the time"?

There are **two separate programs**, and they differ:

| Program | systemd option | Behaviour |
|---------|----------------|-----------|
| Icon + window (`run.py`) | **user service** (`systemd --user`) or desktop autostart | Needs you logged into the desktop (it draws on screen). Stays alive the whole time you're logged in. Cannot show an icon when nobody is logged in. |
| HTTP sniffer (`http_logger.py`) | **system service** (root) | No window. Can run continuously, even before login → captures HTTP all day. *This* is the right candidate for systemd. |

> **Say this:** "The GUI runs while I'm logged into the desktop. The optional
> sniffer can run as a system-level systemd service to capture HTTP nonstop."

---

## 8. Quick Q&A answers

- **Needs root?** No for SSH/passwords/devices (user just needs the `adm`
  group, default on Ubuntu; `journalctl -k` needs no sudo). Only the optional
  HTTP sniffer needs root, because reading the network card is privileged.
- **Slows the machine?** No — read-only and on-demand.
- **Sends data anywhere?** No — everything stays on the machine.
- **Why no AI for the English?** Fixed templates are fast, can't hallucinate
  wrong facts in a demo, and are fully auditable.
- **Portable to other Linux?** Mostly — log paths are standard on
  Debian/Ubuntu; `journalctl` (which we use for devices) is universal.
