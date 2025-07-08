"""App Settings (now loaded from AfcTrackSettings singleton model)"""

from .models import AfcTrackSettings

def get_afctrack_settings():
    settings_obj = AfcTrackSettings.get_solo()
    return {
        "AFCTRACK_FC_GROUPS": settings_obj.get_fc_groups(),
        "AFCTRACK_FLEET_TYPE_GROUPS": settings_obj.get_fleet_type_groups(),
        "AFCTRACK_BUDGET": settings_obj.afc_budget,
        "AFCTRACK_FLEET_TYPES": settings_obj.get_fleet_types(),
        "AFCTRACK_COMMS_OPTIONS": settings_obj.get_comms_options(),
        "AFCTRACK_POINTS": settings_obj.get_points(),
    }

# Provide module-level variables for backward compatibility
try:
    _settings = get_afctrack_settings()
    AFCTRACK_FC_GROUPS = _settings["AFCTRACK_FC_GROUPS"]
    AFCTRACK_FLEET_TYPE_GROUPS = _settings["AFCTRACK_FLEET_TYPE_GROUPS"]
    DEFAULT_BUDGET = _settings["AFCTRACK_BUDGET"]
    FLEET_TYPES = _settings["AFCTRACK_FLEET_TYPES"]
    COMMS_OPTIONS = _settings["AFCTRACK_COMMS_OPTIONS"]
    POINTS = _settings["AFCTRACK_POINTS"]
except Exception:
    # Fallback defaults if the singleton is not yet created
    AFCTRACK_FC_GROUPS = ["junior fc", "fc"]
    AFCTRACK_FLEET_TYPE_GROUPS = ["junior fc", "fc", "Mining Officer"]
    DEFAULT_BUDGET = 3000000000
    FLEET_TYPES = ["Peacetime", "Strat OP", "Mining", "Hive", "CTA", "ADM", "Home Defense", "Incursion", "Caps"]
    COMMS_OPTIONS = [
        {"name": "Capital OP", "url": "https://tinyurl.com/igc-cap-op"},
        {"name": "OP 1 - Tantari blueball again", "url": "http://tinyurl.com/igc-op1"},
        {"name": "OP 2 - Shabi Yilibybe Always Feeds", "url": "http://tinyurl.com/igc-op2"},
        {"name": "OP 3 - Lybs Failed", "url": "http://tinyurl.com/igc-op3-channel"},
        {"name": "OP 4 - Aidan Golden Eggs", "url": "http://tinyurl.com/igc-op4-channel"},
        {"name": "OP 5 - Dave missed anchor time", "url": "http://tinyurl.com/igc-op5-channel"},
        {"name": "OP 6 - Badsaki hide in astra", "url": "http://tinyurl.com/igc-op6"},
        {"name": "OP 7 - Aura lost an Occator with 3 Astra", "url": "http://tinyurl.com/igc-op7-channel"},
        {"name": "OP 8 - Mirar selling Ishtar", "url": "http://tinyurl.com/igc-op8-channel"}

    ]
    POINTS = {
        'Peacetime': 0.5,
        'Strat OP': 1,
        'Caps': 1,
        'CTA': 1,
        'Hive': 1.5,
        'ADM': 0.5,
        'Home Defense': 0.5,
        'Incursion': 0.5,
    }