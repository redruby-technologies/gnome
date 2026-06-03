#!/usr/bin/env bash
#
# install.sh — make the System Activity Monitor start AUTOMATICALLY.
# =================================================================
# It sets up two things:
#
#   1. GUI service  (user)   → the top-bar icon + window start on login
#   2. HTTP sniffer (system) → captures insecure HTTP all the time
#
# The app reads the logs directly each time you open or Refresh it — there is
# NO database and NO background collector. If a log is empty or already gone,
# the matching card simply shows empty.
#
# Item 1 needs NO sudo (it is a *user* service). Item 2 needs root ONCE during
# install, because sniffing the network card is privileged — so it is a
# *system* service. The script will ask before setting it up.
#
# Safe to re-run. Usage:
#     bash install.sh
#
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(command -v python3)"
USER_UNIT_DIR="$HOME/.config/systemd/user"
LOGFILE="$HOME/.local/share/sysactivity/http_sites.log"
IFACE="$(ip route 2>/dev/null | awk '/default/{print $5; exit}')"

echo "Project    : $PROJECT_DIR"
echo "Python     : $PYTHON"
echo "Network if : ${IFACE:-auto-detect}"
mkdir -p "$USER_UNIT_DIR"

# Clean up the old database collector if a previous install set it up.
systemctl --user disable --now sysactivity-collector.timer 2>/dev/null || true
rm -f "$USER_UNIT_DIR/sysactivity-collector.timer" \
      "$USER_UNIT_DIR/sysactivity-collector.service"

# ─────────────────────────────────────────────────────────────────────
# 1) USER SERVICE — the top-bar icon + window (auto-start on login)
# ─────────────────────────────────────────────────────────────────────
cat > "$USER_UNIT_DIR/sysactivity-gui.service" <<EOF
[Unit]
Description=System Activity Monitor - top-bar icon and window
PartOf=graphical-session.target
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$PYTHON $PROJECT_DIR/run.py
Restart=on-failure

[Install]
WantedBy=graphical-session.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now sysactivity-gui.service || \
    echo "(note: GUI service will start on your next login)"
echo "✓ User service installed: GUI (icon + window)."

# ─────────────────────────────────────────────────────────────────────
# 2) SYSTEM SERVICE — the HTTP sniffer (needs root, so it uses sudo)
# ─────────────────────────────────────────────────────────────────────
echo
read -rp "Also set up the HTTP sniffer to run automatically at boot? (needs sudo) [y/N] " ans
if [[ "${ans,,}" == "y" ]]; then
    IFACE_ARG=""
    [ -n "$IFACE" ] && IFACE_ARG="-i $IFACE"
    sudo tee /etc/systemd/system/sysactivity-sniffer.service >/dev/null <<EOF
[Unit]
Description=System Activity Monitor - insecure HTTP sniffer
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$PYTHON $PROJECT_DIR/http_logger.py $IFACE_ARG --logfile $LOGFILE
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable --now sysactivity-sniffer.service
    echo "✓ HTTP sniffer system service installed and started."
else
    echo "• Skipped the HTTP sniffer service. Re-run install.sh anytime to add it."
fi

echo
echo "All set. Check it with:"
echo "  systemctl --user status sysactivity-gui.service"
echo "  systemctl status sysactivity-sniffer.service   # if you enabled it"
echo
echo "TIP: to keep the GUI running even when logged out, run once:"
echo "  sudo loginctl enable-linger $USER"
