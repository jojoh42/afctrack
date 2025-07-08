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
        {"name": "Capital OP", "url": "https://tinyurl.com/ywwp85u9"},
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