from django.db import models
from django.db.models import Count
from django.contrib.auth.models import User
from afat.models import FatLink
from django.conf import settings
from datetime import datetime

# Get payment amounts from settings (from app_settings.py)
FC_Payment_Ammount = getattr(settings, "FC_Payment_Ammount", 200000000)
FC_Payment_Ammount_Max = getattr(settings, "FC_Payment_Ammount_Max", 1000000000)
JFC_Payment_Ammount = getattr(settings, "JFC_Payment_Ammount", 100000000)
JFC_Payment_Ammount_Max = getattr(settings, "JFC_Payment_Ammount_Max", 500000000)

# Doctrine points
POINTS = {
    'PCT/Roam': 0.5,
    'Strat OP': 1,
    'Hive': 1.5
}

def get_fleet_counts_and_payment(budget):
    """
    Get fleet counts and calculate the payment for each user based on their fleet count and doctrine.
    This function returns a list of dictionaries with player names and their corresponding payments.
    """
    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get the primary keys of users in the "jfc" or "fc" groups
    fc_users_ids = User.objects.filter(groups__name__in=["jfc", "fc"]).values_list('id', flat=True)

    # Filter FatLink by those users and the current month/year
    fleet_counts = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('creator_id__username', 'fleet_type')\
     .annotate(fleet_count=Count('id'))\
     .order_by('creator_id__username', 'fleet_type')

    # Aggregate fleet counts and doctrine points
    player_data = {}
    total_fleet_points = 0

    for player in fleet_counts:
        player_name = player['creator_id__username']
        fleet_type = player['fleet_type']
        fleet_count = player['fleet_count']
        
        # Get points for the doctrine
        fleet_points = POINTS.get(fleet_type, 0)

        if player_name not in player_data:
            player_data[player_name] = {
                'total_fleet_count': 0,
                'total_fleet_points': 0,
            }

        # Accumulate fleet counts and points for the player
        player_data[player_name]['total_fleet_count'] += fleet_count
        player_data[player_name]['total_fleet_points'] += fleet_points * fleet_count
        total_fleet_points += fleet_points * fleet_count

    # Calculate ISK per point if the total score is greater than 0
    if total_fleet_points > 0:
        isk_per_point = budget / total_fleet_points
    else:
        isk_per_point = 0

    # Calculate the payment for each player
    player_payments = []
    for player_name, data in player_data.items():
        # Calculate the payment based on the doctrine points
        payment = data['total_fleet_points'] * isk_per_point
        player_payments.append({
            'player_name': player_name,
            'fleet_count': data['total_fleet_count'],
            'payment': payment,
        })

    return player_payments


def get_fleet_count_by_doctrine():
    """
    Get doctrine counts for the current month/year and return the results as a list of dictionaries.
    """
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get the primary keys of users in the "jfc" or "fc" groups
    fc_users_ids = User.objects.filter(groups__name__in=["jfc", "fc"]).values_list('id', flat=True)

    # Filter FatLink by those users and the current month/year
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
    current_month = datetime.now().month
    current_year = datetime.now().year

    fc_users_ids = User.objects.filter(groups__name__in=["jfc", "fc"]).values_list('id', flat=True)

    fleet_count_type = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('fleet_type')\
     .annotate(type_count=Count('id'))\
     .order_by('-type_count')

    return fleet_count_type
