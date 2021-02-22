from pathlib import Path

from single_version import get_version


__version__ = get_version('tumtum', Path(__file__).parent.parent)
