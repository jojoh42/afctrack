from django.db import models
from django.contrib.auth.models import User
# from .app_settings import POINTS  # Removed to fix circular import

class General(models.Model):
    """Meta model for app permissions"""
    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", "can create an MOTD"),
        )

# Doctrine points
# POINTS = POINTS # This line is removed as per the edit hint.

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