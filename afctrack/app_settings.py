"""App Settings"""

# Django
from django.conf import settings

# Gruppennamen für Filter in afctrack, mit Möglichkeit zur Überschreibung in settings.py
AFCTRACK_FC_GROUPS = getattr(settings, "AFCTRACK_FC_GROUPS", ["junior fc", "fc"])
AFCTRACK_FLEET_TYPE_GROUPS = getattr(settings, "AFCTRACK_FLEET_TYPE_GROUPS", ["junior fc", "fc", "Mining Officer"])

# Standard-Budget für Fleet-Zahlungen (3 Milliarden ISK)
DEFAULT_BUDGET = getattr(settings, "AFCTRACK_BUDGET", "3000000000")

# Flotten-Typen
FLEET_TYPES = getattr(settings, "AFCTRACK_FLEET_TYPES", ["Peacetime", "StratOP", "Mining", "Hive", "CTA"])

# Kommunikations-Optionen
COMMS_OPTIONS = getattr(settings, "AFCTRACK_COMMS_OPTIONS", [
    {"name": "Capital OP", "url": "https://tinyurl.com/ywwp85u9"},
    {"name": "OP1-Stratergic", "url": "https://tinyurl.com/IGCOP1"},
    {"name": "OP2-Home Defense", "url": "https://tinyurl.com/IGCOP2"},
    {"name": "OP3-CTA", "url": "https://tinyurl.com/3m64n62p"},
    {"name": "OP4-Moon Event", "url": "https://tinyurl.com/mrh6436r"},
    {"name": "OP5-ICE Event", "url": "https://tinyurl.com/mr5sspda"},
    {"name": "OP6 - Peacetime", "url": "https://tinyurl.com/ymusr8k9"},
    {"name": "OP7 - Peacetime", "url": "https://tinyurl.com/bp7r58ep"},
    {"name": "OP8 - Peacetime", "url": "https://tinyurl.com/2dbcwwcu"}
])

# Points for each fleet type
POINTS = getattr(settings, "AFCTRACK_POINTS", {
    'Peacetime': 0.5,
    'Strat OP': 1,
    'CTA': 1,
    'Hive': 1.5
})