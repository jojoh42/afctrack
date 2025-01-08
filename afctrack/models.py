from django.db import models
from django.contrib.auth.models import User

class General(models.Model):
    """Meta model for app permissions"""
    
    class Meta:
        """Meta definitions"""
        
        # This model is not intended to be managed by Django (e.g., not to be migrated)
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", "Can access this app"),
        )

# Doctrine points
POINTS = {
    'Peacetime': 0.5,
    'Strat OP': 1,
    'Hive': 1.5
}

def get_current_month_and_year():
    """
    Helper function to get the current month and year.
    """
    current_month = datetime.now().month
    current_year = datetime.now().year
    return current_month, current_year

# Remove the following functions from models.py and move them to views.py
# def get_fleet_counts_and_payment(budget):
# def get_fleet_count_by_doctrine():
# def get_fleet_count_by_type():