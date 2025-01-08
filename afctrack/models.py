from django.db import models
from django.db.models import Count, Sum
from django.contrib.auth.models import User
from datetime import datetime

class General(models.Model):
    """Meta model for app permissions"""
    
    class Meta:
        """Meta definitions"""
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

def get_fleet_counts_and_payment(budget):
    """
    Get fleet counts and calculate the payment for each user based on their fleet count, doctrine, and participants.
    Returns a list of dictionaries with player names, payments, and average participants.
    """
    current_month, current_year = get_current_month_and_year()

    # Get the primary keys of users in the "jfc" or "fc" groups
    fc_users_ids = User.objects.filter(groups__name__in=["jfc", "fc"]).values_list('id', flat=True)

    # Filter FatLink by those users and the current month/year, annotate with participant count
    fleet_counts = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('creator_id__username', 'id', 'fleet_type')\
     .annotate(
        fleet_count=Count('id'),
        total_participants=Sum('fat__id')  # Sum of related Fat entries (replace with correct annotation if needed)
    ).order_by('creator_id__username', 'fleet_type')

    # Aggregate fleet counts, doctrine points, and participants
    player_data = {}
    total_fleet_points = 0

    for fleet in fleet_counts:
        player_name = fleet['creator_id__username']
        # Continue with your logic here...

    # Return the aggregated data
    return player_data