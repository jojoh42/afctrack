from django.db import models
from django.contrib.auth.models import User
from .app_settings import POINTS
from solo.models import SingletonModel  # type: ignore
import json

class General(models.Model):
    """Meta model for app permissions"""
    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", "can create an MOTD"),
        )

# Doctrine points
POINTS = POINTS

def get_current_month_and_year():
    """
    Helper function to get the current month and year.
    """
    from datetime import datetime
    current_month = datetime.now().month
    current_year = datetime.now().year
    return current_month, current_year

class FittingsDoctrine(models.Model):
    """
    Model for doctrines stored in the fittings_doctrine table in the aa_dev database.
    """
    name = models.CharField(max_length=255, unique=True)
    class Meta:
        db_table = "fittings_doctrine"
        managed = False

# Singleton settings model for admin editing
class AfcTrackSettings(SingletonModel):
    afc_fc_groups = models.CharField(
        max_length=255,
        default="junior fc,fc",
        help_text="Comma-separated group names for FCs"
    )
    afc_fleet_type_groups = models.CharField(
        max_length=255,
        default="junior fc,fc,Mining Officer",
        help_text="Comma-separated group names for fleet types"
    )
    afc_budget = models.BigIntegerField(
        default=3000000000,  # type: ignore
        help_text="Default budget for fleet payments"
    )
    afc_fleet_types = models.CharField(
        max_length=255,
        default="Peacetime,Strat OP,Mining,Hive,CTA,ADM,Home Defense,Incursion,Caps",
        help_text="Comma-separated fleet types"
    )
    afc_comms_options = models.TextField(
        default='[{"name": "Capital OP", "url": "https://tinyurl.com/ywwp85u9"}]',
        help_text="JSON list of comms options (name/url pairs)"
    )
    afc_points = models.TextField(
        default='{"Peacetime": 0.5, "Strat OP": 1, "Caps": 1, "CTA": 1, "Hive": 1.5, "ADM": 0.5, "Home Defense": 0.5, "Incursion": 0.5}',
        help_text="JSON object mapping fleet types to points"
    )

    def get_fc_groups(self):
        return [g.strip() for g in str(self.afc_fc_groups).split(',') if g.strip()]

    def get_fleet_type_groups(self):
        return [g.strip() for g in str(self.afc_fleet_type_groups).split(',') if g.strip()]

    def get_fleet_types(self):
        return [g.strip() for g in str(self.afc_fleet_types).split(',') if g.strip()]

    def get_comms_options(self):
        try:
            return json.loads(str(self.afc_comms_options))
        except Exception:
            return []

    def get_points(self):
        try:
            return json.loads(str(self.afc_points))
        except Exception:
            return {}