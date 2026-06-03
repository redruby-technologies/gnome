"""
ui.py — the window that opens when the top-bar icon is clicked.
================================================================
A clean GTK3 window with one card per activity. Each card shows:
  * a heading (e.g. "Remote Connections (SSH)")
  * a one-line summary in bold
  * the detailed sentences underneath

A "Refresh" button re-reads the logs so the demo can show live updates
(plug a USB stick → click Refresh → it appears).
"""

from __future__ import annotations

import datetime as _dt

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango  # noqa: E402

from . import nl  # noqa: E402
from .logsrc.common import today  # noqa: E402

# A small stylesheet so it looks presentable for a company demo.
_CSS = b"""
window { background-color: #f4f6fb; }
.title-bar { font-size: 17px; font-weight: bold; color: #1a2233; padding: 6px 4px; }
.subtitle { color: #5a6472; font-size: 12px; padding-bottom: 8px; }
.card { background-color: #ffffff; border-radius: 12px; padding: 14px 16px;
        border: 1px solid #e3e8f0; margin: 6px 2px; }
.card-title { font-size: 14px; font-weight: bold; color: #2563eb; }
.headline { font-size: 13px; font-weight: bold; color: #111827; padding: 4px 0; }
.item { color: #374151; font-size: 12px; padding: 2px 0; }
.empty { color: #9aa3af; font-style: italic; font-size: 12px; }
.icon { font-size: 18px; }
"""

# An emoji per activity, matched by title keyword — purely cosmetic.
_ICONS = {
    "SSH": "🔗",
    "Password": "🔑",
    "Devices": "🔌",
    "HTTP": "🌐",
}


def _icon_for(title: str) -> str:
    for key, emoji in _ICONS.items():
        if key.lower() in title.lower():
            return emoji
    return "•"


class ActivityWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Today's System Activity")
        self.set_default_size(560, 640)
        self.set_position(Gtk.WindowPosition.CENTER)

        provider = Gtk.CssProvider()
        provider.load_from_data(_CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(outer)

        # Which day we are showing, and the current search text.
        self._selected_day = today()
        self._search_text = ""

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header.set_margin_top(12)
        header.set_margin_start(16)
        header.set_margin_end(16)

        # Title on the left; search box + date picker on the right.
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label="Today's System Activity", xalign=0)
        title.get_style_context().add_class("title-bar")
        title_row.pack_start(title, True, True, 0)
        title_row.pack_end(self._build_date_picker(), False, False, 0)
        title_row.pack_end(self._build_search_box(), False, False, 0)
        header.pack_start(title_row, False, False, 0)

        self._sub = Gtk.Label(
            label="A simple summary of what happened on this computer today.",
            xalign=0)
        self._sub.get_style_context().add_class("subtitle")
        header.pack_start(self._sub, False, False, 0)
        outer.pack_start(header, False, False, 0)

        # Scrollable list of cards
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._cards_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._cards_box.set_margin_start(12)
        self._cards_box.set_margin_end(12)
        scroller.add(self._cards_box)
        outer.pack_start(scroller, True, True, 0)

        # Footer with Refresh + Close
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer.set_margin_top(8)
        footer.set_margin_bottom(12)
        footer.set_margin_start(16)
        footer.set_margin_end(16)
        refresh = Gtk.Button(label="↻  Refresh")
        refresh.connect("clicked", lambda *_: self.reload())
        close = Gtk.Button(label="Close")
        close.connect("clicked", lambda *_: self.hide())
        footer.pack_start(refresh, False, False, 0)
        footer.pack_end(close, False, False, 0)
        outer.pack_start(footer, False, False, 0)

        # Hide instead of destroy, so the tray icon can reopen it.
        self.connect("delete-event", lambda *_: (self.hide(), True)[1])

        self.reload()

    def reload(self, *_):
        """Re-read the logs for the selected day and redraw the cards.

        Used when opening the window and when clicking Refresh. Changing the
        calendar date or typing in search also calls _render().
        """
        self._render()

    def _render(self):
        """Rebuild every card by reading the logs for the selected day,
        filtered by the current search text."""
        self._update_date_ui()
        for child in self._cards_box.get_children():
            self._cards_box.remove(child)
        for section in nl.all_sections(self._selected_day):
            card = self._build_card(section, self._search_text)
            self._cards_box.pack_start(card, False, False, 0)
        self._cards_box.show_all()

    # ── Search box ────────────────────────────────────────────────────
    def _build_search_box(self) -> Gtk.SearchEntry:
        """A box to filter the visible lines (by user, IP, device, site…)."""
        entry = Gtk.SearchEntry()
        entry.set_placeholder_text("Search…")
        entry.set_width_chars(18)
        entry.connect("search-changed", self._on_search_changed)
        self._search_entry = entry
        return entry

    def _on_search_changed(self, entry):
        self._search_text = entry.get_text().strip().lower()
        self._render()      # re-read for the selected day and filter

    # ── Date picker ───────────────────────────────────────────────────
    def _build_date_picker(self) -> Gtk.MenuButton:
        """A button showing the chosen date; clicking it opens a calendar."""
        self._calendar = Gtk.Calendar()
        d = self._selected_day
        self._calendar.select_month(d.month - 1, d.year)   # Gtk months are 0-based
        self._calendar.select_day(d.day)
        self._calendar.connect("day-selected", self._on_calendar_day)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for m in ("set_margin_top", "set_margin_bottom",
                  "set_margin_start", "set_margin_end"):
            getattr(box, m)(8)
        box.pack_start(self._calendar, False, False, 0)
        jump = Gtk.Button(label="Jump to Today")
        jump.connect("clicked", self._on_jump_today)
        box.pack_start(jump, False, False, 0)
        box.show_all()

        self._date_popover = Gtk.Popover()
        self._date_popover.add(box)

        self._date_btn = Gtk.MenuButton()
        self._date_btn.set_popover(self._date_popover)
        self._date_btn.set_label(self._date_text())
        return self._date_btn

    def _date_text(self) -> str:
        if self._selected_day == today():
            return "📅  Today"
        return self._selected_day.strftime("📅  %b %-d, %Y")

    def _update_date_ui(self):
        """Keep the button label and the subtitle in sync with the date."""
        self._date_btn.set_label(self._date_text())
        if self._selected_day == today():
            self._sub.set_text(
                "A simple summary of what happened on this computer today.")
        else:
            self._sub.set_text(self._selected_day.strftime(
                "Activity recorded on %A, %b %-d, %Y."))

    def _on_calendar_day(self, cal):
        year, month0, day = cal.get_date()
        new_day = _dt.date(year, month0 + 1, day)
        if new_day == self._selected_day:
            return
        self._selected_day = new_day
        self._render()      # re-read the logs for the newly chosen day

    def _on_jump_today(self, *_):
        t = today()
        self._calendar.select_month(t.month - 1, t.year)
        self._calendar.select_day(t.day)   # fires _on_calendar_day → reload
        self._date_popover.popdown()

    def _build_card(self, section: dict, term: str = "") -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.get_style_context().add_class("card")

        # Apply the search filter. If the term matches the section name itself
        # (e.g. "ssh"), keep all of its lines; otherwise keep matching lines.
        items = section["items"]
        if term and term not in section["title"].lower():
            items = [t for t in items if term in t.lower()]

        # Title row: emoji + section name
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon = Gtk.Label(label=_icon_for(section["title"]))
        icon.get_style_context().add_class("icon")
        name = Gtk.Label(label=section["title"], xalign=0)
        name.get_style_context().add_class("card-title")
        row.pack_start(icon, False, False, 0)
        row.pack_start(name, False, False, 0)
        card.pack_start(row, False, False, 0)

        headline = Gtk.Label(label=section["headline"], xalign=0)
        headline.get_style_context().add_class("headline")
        headline.set_line_wrap(True)
        headline.set_line_wrap_mode(Pango.WrapMode.WORD)
        card.pack_start(headline, False, False, 0)

        if section["empty"]:
            note = Gtk.Label(label="Nothing to report.", xalign=0)
            note.get_style_context().add_class("empty")
            card.pack_start(note, False, False, 0)
        elif not items:
            note = Gtk.Label(label=f"No matches for “{term}”.", xalign=0)
            note.get_style_context().add_class("empty")
            card.pack_start(note, False, False, 0)
        else:
            for text in items:
                lbl = Gtk.Label(label="•  " + text, xalign=0)
                lbl.get_style_context().add_class("item")
                lbl.set_line_wrap(True)
                lbl.set_line_wrap_mode(Pango.WrapMode.WORD)
                card.pack_start(lbl, False, False, 0)
        return card
