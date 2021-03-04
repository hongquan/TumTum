from pathlib import Path

import gi
import tomlkit
from pydantic import ValidationError

gi.require_version('Gio', '2.0')

from .consts import SHORT_NAME, DEFAULT_SETTINGS
from .models import AppSettings


# Folder to look for icon, glade files
# - If this app is installed in ~/.local/bin and run from there, look for ~/.local/share/tumtum
# - If this app is install in /usr/local/bin and run from there, look for /usr/local/share/tumtum
# - If this app is install in /app/, which is the case of Faltpak container, look for /app/share/tumtum
# - If this app is run from source, look in the source folder

DOT_LOCAL = Path('~/.local').expanduser()


def get_location_prefix() -> Path:
    top_app_dir = Path(__file__).parent.parent.resolve()
    str_top_app_dir = str(top_app_dir)
    if str_top_app_dir.startswith('/usr/local/'):
        return Path('/usr/local/')
    if str_top_app_dir.startswith('/usr/'):
        return Path('/usr/')
    if str_top_app_dir.startswith('/app/'):
        return Path('/app/')
    if str_top_app_dir.startswith(str(DOT_LOCAL)):
        return DOT_LOCAL
    # Run from source
    return top_app_dir


def get_ui_folder() -> Path:
    prefix = get_location_prefix()
    # Note: The trailing slash "/" is stripped by Path()
    str_prefix = str(prefix)
    if str_prefix.startswith(('/usr', '/app', str(DOT_LOCAL))):
        return prefix / 'share' / SHORT_NAME
    # Run from source
    return prefix / 'data'


def get_locale_folder() -> Path:
    prefix = get_location_prefix()
    str_prefix = str(prefix)
    if str_prefix.startswith(('/usr', '/app', str(DOT_LOCAL))):
        return prefix / 'share' / 'locale'
    # Run from source
    return prefix / 'po'


def get_ui_filepath(filename: str) -> Path:
    ui_folder = get_ui_folder()
    return ui_folder / filename


def get_ui_source(filename: str) -> str:
    filepath = get_ui_filepath(filename)
    return filepath.read_text()


def get_config_path() -> Path:
    return Path(f'~/.config/{SHORT_NAME}.toml').expanduser()


def load_config() -> AppSettings:
    filepath = get_config_path()
    data = {}
    if filepath.exists():
        data = tomlkit.parse(filepath.read_text())
        try:
            return AppSettings.parse_obj(data)
        except ValidationError:
            pass
    if not data:
        data = DEFAULT_SETTINGS
    return AppSettings.parse_obj(data)
