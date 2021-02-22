
from typing import Optional

import gi
from logbook import Logger
gi.require_version('Gtk', '3.0')
gi.require_version('Gio', '2.0')

from gi.repository import Gtk, Gio


logger = Logger(__name__)


def build_app_menu_model() -> Gio.Menu:
    menu = Gio.Menu()
    menu.append('About', 'app.about')
    menu.append('Quit', 'app.quit')
    return menu


def update_progress(bar: Gtk.ProgressBar, jump: Optional[float] = None):
    # FIXME: Due to async operation, this function may be called after bar has been destroyed.
    if jump is None:
        f = bar.get_fraction()
        bar.set_fraction(f + 0.05)
    else:
        bar.set_fraction(jump)
    f = bar.get_fraction()
    if f >= 1:
        bar.set_visible(False)
        return False
    return True
