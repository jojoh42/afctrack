from django.db import models
from django.db.models import Count, Sum
from django.contrib.auth.models import User
from datetime import datetime
from decimal import Decimal
from afat.models import FatLink, Fat  # Keep this import

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
    print(f"FC Users IDs: {fc_users_ids}")

    # Filter FatLink by those users and the current month/year, annotate with participant count
    fleet_counts = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('creator_id__username', 'id', 'fleet_type')\
     .annotate(
        fleet_count=Count('id'),
        total_participants=Sum('afat_fats__participants')  # Ensure correct field name for related Fat entries
    ).order_by('creator_id__username', 'fleet_type')
    print(f"Fleet Counts: {fleet_counts}")

    # Aggregate fleet counts, doctrine points, and participants
    player_data = {}
    total_fleet_points = Decimal(0)  # Initialize as Decimal

    for fleet in fleet_counts:
        player_name = fleet['creator_id__username']
        fleet_type = fleet['fleet_type']
        fleet_count = fleet['fleet_count']
        total_participants = fleet['total_participants'] or 0  # Ensure total_participants is not None

        if player_name not in player_data:
            player_data[player_name] = {
                'total_payment': Decimal(0),
                'total_fleets': 0,
                'total_participants': 0
            }

        doctrine_points = POINTS.get(fleet_type, 1)
        payment = fleet_count * doctrine_points * total_participants
        player_data[player_name]['total_payment'] += Decimal(payment)
        player_data[player_name]['total_fleets'] += fleet_count
        player_data[player_name]['total_participants'] += total_participants
        total_fleet_points += Decimal(fleet_count * doctrine_points)  # Update total_fleet_points

    # Calculate the average participants and normalize payments
    budget = Decimal(budget)  # Convert budget to Decimal
    for player_name, data in player_data.items():
        data['average_participants'] = data['total_participants'] / data['total_fleets'] if data['total_fleets'] > 0 else 0
        data['normalized_payment'] = data['total_payment'] / total_fleet_points * budget if total_fleet_points > 0 else 0

    # Return the aggregated data
    print(f"Player Data: {player_data}")
    return player_data

def get_doctrine_counts(month, year):
    """
    Get doctrine counts for the given month and year.
    """
    # Implement the logic to get doctrine counts
    # Example:
    doctrine_counts = FatLink.objects.filter(
        created__month=month,
        created__year=year
    ).values('fleet_type').annotate(
        count=Count('id')
    ).order_by('fleet_type')

    return doctrine_counts

def get_fleet_type_amount(month, year):
    """
    Get fleet type amounts for the given month and year.
    """
    # Implement the logic to get fleet type amounts
    # Example:
    fleet_type_amounts = FatLink.objects.filter(
        created__month=month,
        created__year=year
    ).values('fleet_type').annotate(
        count=Count('id')
    ).order_by('fleet_type')

    return fleet_type_amounts