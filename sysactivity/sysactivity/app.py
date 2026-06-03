"""
app.py — the top-bar icon and application entry point.
======================================================
This puts an icon in the GNOME top bar (next to wifi/volume). Clicking it
shows a menu; "Open Today's Activity" opens the window from ui.py.

Ubuntu 24.04's top bar shows these "AppIndicator" icons via its built-in
extension, so this is the fastest way to get a wifi-style icon without
writing a full GNOME Shell extension.

If the AppIndicator library is not installed, we DON'T crash — we just open
the window directly so the demo still works.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa: E402

from .ui import ActivityWindow  # noqa: E402

APP_ID = "system-activity-monitor"


def _load_indicator():
    """Try the modern Ayatana indicator, then the older one. Return module or None."""
    for ns in ("AyatanaAppIndicator3", "AppIndicator3"):
        try:
            gi.require_version(ns, "0.1")
            if ns == "AyatanaAppIndicator3":
                from gi.repository import AyatanaAppIndicator3 as mod
            else:
                from gi.repository import AppIndicator3 as mod
            return mod
        except (ValueError, ImportError):
            continue
    return None


class TrayApp:
    def __init__(self):
        self.window = ActivityWindow()
        self.indicator_mod = _load_indicator()
        if self.indicator_mod:
            self._build_tray_icon()
        else:
            # No tray library — open the window directly so the demo still runs.
            print("[note] AppIndicator library not found — opening window directly.")
            self.window.show_all()

    def _build_tray_icon(self):
        mod = self.indicator_mod
        self.indicator = mod.Indicator.new(
            APP_ID,
            "security-high-symbolic",                 # a shield-style stock icon
            mod.IndicatorCategory.SYSTEM_SERVICES)
        self.indicator.set_status(mod.IndicatorStatus.ACTIVE)
        self.indicator.set_title("Today's System Activity")
        self.indicator.set_menu(self._build_menu())

    def _build_menu(self) -> Gtk.Menu:
        menu = Gtk.Menu()

        open_item = Gtk.MenuItem(label="📋  Open Today's Activity")
        open_item.connect("activate", self._open_window)
        menu.append(open_item)

        refresh_item = Gtk.MenuItem(label="↻  Refresh now")
        refresh_item.connect("activate", lambda *_: self.window.reload())
        menu.append(refresh_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda *_: Gtk.main_quit())
        menu.append(quit_item)

        menu.show_all()
        return menu

    def _open_window(self, *_):
        self.window.reload()
        self.window.show_all()
        self.window.present()


def main():
    TrayApp()
    # Ctrl-C friendly
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 2, Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    main()
