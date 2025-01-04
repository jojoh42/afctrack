"""App Configuration"""

# Django
from django.apps import AppConfig

# AA afctrack App
from afctrack import __version__


class afctrackConfig(AppConfig):
    """App Config"""

    name = "FC Activity Tracker"
    label = "FC Activity Tracker"
    verbose_name = f"FC Activity Tracker v{__version__}"
