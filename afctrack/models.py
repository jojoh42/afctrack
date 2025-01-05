from django.db import models
from django.db.models import Count
from django.contrib.auth.models import User, Group
from afat.models import FatLink
from django.conf import settings
from datetime import datetime

# Get payment amounts from settings (from app_settings.py)
FC_Payment_Ammount = getattr(settings, "FC_Payment_Ammount", 200000000)
FC_Payment_Ammount_Max = getattr(settings, "FC_Payment_Ammount_Max", 1000000000)
JFC_Payment_Ammount = getattr(settings, "JFC_Payment_Ammount", 100000000)
JFC_Payment_Ammount_Max = getattr(settings, "JFC_Payment_Ammount_Max", 500000000)

def get_fleet_counts_and_payment():
    """
    Get fleet counts and calculate the payment for each user based on their fleet count.
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
    ).values('creator_id__username')\
     .annotate(fleet_count=Count('id'))\
     .order_by('-fleet_count')

    # Create a list of player payments
    player_payments = []

    # Calculate payment for each player
    for player in fleet_counts:
        player_name = player['creator_id__username']
        fleet_count = player['fleet_count']
        
        # Determine whether the user is an FC or JFC
        user = User.objects.get(username=player_name)
        if user.groups.filter(name="fc").exists():
            base_payment = FC_Payment_Ammount
            max_payment = FC_Payment_Ammount_Max
        else:
            base_payment = JFC_Payment_Ammount
            max_payment = JFC_Payment_Ammount_Max
        
        # Calculate the payment amount per fleet
        if fleet_count > 0:
            payment_per_fleet = base_payment * fleet_count
        else:
            payment_per_fleet = 0
        
        # Ensure the payment amount doesn't exceed the max allowed
        final_payment = min(payment_per_fleet, max_payment)

        # Add the payment details to the list
        player_payments.append({
            'player_name': player_name,
            'fleet_count': fleet_count,
            'payment': final_payment
        })

    return player_payments


def get_fleet_count_by_doctrine():
    """
    Get doctrine counts for the current month/year and return the results as a list of dictionaries.
    """
    # Get the current month and year
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

    # Return the doctrine count data
    return fleet_count_doctrine


def get_fleet_count_by_type():
    """
    Get fleet type counts for the current month/year and return the results as a list of dictionaries.
    """
    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get the primary keys of users in the "jfc" or "fc" groups
    fc_users_ids = User.objects.filter(groups__name__in=["jfc", "fc"]).values_list('id', flat=True)

    # Filter FatLink by those users and the current month/year
    fleet_count_type = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('fleet_type')\
     .annotate(type_count=Count('id'))\
     .order_by('-type_count')

    # Return the fleet type count data
    return fleet_count_type
