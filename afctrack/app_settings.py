"""App Settings"""

# Django
from django.conf import settings

# Gruppennamen für Filter in afctrack, mit Möglichkeit zur Überschreibung in settings.py
AFCTRACK_FC_GROUPS = getattr(settings, "AFCTRACK_FC_GROUPS", ["junior fc", "fc"])
AFCTRACK_FLEET_TYPE_GROUPS = getattr(settings, "AFCTRACK_FLEET_TYPE_GROUPS", ["junior fc", "fc", "Mining Officer"])