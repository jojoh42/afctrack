"""App Configuration"""

# Django
from django.apps import AppConfig

# AA afctrack App
from afctrack import __version__


class afctrackConfig(AppConfig):
    """App Config"""

    name = "afctrack"
    label = "afctrack"
    verbose_name = f"afctrack App v{__version__}"
