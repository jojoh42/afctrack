from django.db import models
from django.db.models import Count, Sum
from django.contrib.auth.models import User
from afat.models import FatLink, Fat
from datetime import datetime

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
        fleet_id = fleet['id']
        fleet_type = fleet['fleet_type']
        fleet_count = fleet['fleet_count']
        participant_count = fleet['total_participants'] or 0

        # Get points for the doctrine
        fleet_points = POINTS.get(fleet_type, 0)

        if player_name not in player_data:
            player_data[player_name] = {
                'total_fleet_count': 0,
                'total_fleet_points': 0,
                'total_participants': 0,
            }

        # Accumulate fleet counts, points, and participants for the player
        player_data[player_name]['total_fleet_count'] += fleet_count
        player_data[player_name]['total_fleet_points'] += fleet_points * fleet_count
        player_data[player_name]['total_participants'] += participant_count
        total_fleet_points += fleet_points * fleet_count

    # Calculate ISK per point if the total score is greater than 0
    if total_fleet_points > 0:
        isk_per_point = budget / total_fleet_points
        round_isk_per_point = round(isk_per_point)
    else:
        isk_per_point = 0
        round_isk_per_point = round(isk_per_point)

    # Calculate the payment for each player
    player_payments = []
    for player_name, data in player_data.items():
        # Calculate the payment based on the doctrine points
        payment = data['total_fleet_points'] * round_isk_per_point
        # Calculate the average participants per fleet
        avg_participants = data['total_participants'] / data['total_fleet_count'] if data['total_fleet_count'] > 0 else 0
        player_payments.append({
            'player_name': player_name,
            'fleet_count': data['total_fleet_count'],
            'avg_participants': avg_participants,
            'payment': payment,
        })

    return player_payments


def get_fleet_count_by_doctrine():
    """
    Get doctrine counts for the current month/year and return the results as a list of dictionaries.
    """
    current_month, current_year = get_current_month_and_year()

    fc_users_ids = User.objects.filter(groups__name__in=["jfc", "fc"]).values_list('id', flat=True)

    # Query to get doctrine counts for the current month/year
    fleet_count_doctrine = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('doctrine')\
     .annotate(doctrine_count=Count('id'))\
     .order_by('-doctrine_count')

    return fleet_count_doctrine


def get_fleet_count_by_type():
    """
    Get fleet type counts for the current month/year and return the results as a list of dictionaries.
    """
    current_month, current_year = get_current_month_and_year()

    fc_users_ids = User.objects.filter(groups__name__in=["jfc", "fc", "Mining Officer"]).values_list('id', flat=True)

    fleet_count_type = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('fleet_type')\
     .annotate(type_count=Count('id'))\
     .order_by('-type_count')

    return list(fleet_count_type)  # This will convert queryset to a list