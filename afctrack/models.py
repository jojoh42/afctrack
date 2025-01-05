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

def get_fleet_counts():
    """
    Get fleet counts and calculate the payment for each user.
    This function prints the result to the console for each user.
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

    # Calculate payment for each user
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
            payment_per_fleet = base_payment / fleet_count
        else:
            payment_per_fleet = 0
        
        # Ensure the payment amount doesn't exceed the max allowed
        final_payment = min(payment_per_fleet, max_payment)

        print(f"Player Name: {player_name}, Fleets Created: {fleet_count}, Payment Per Fleet: {final_payment}")


def get_fleet_count_doctrine():
    """
    Get doctrine counts for the current month/year and print the results to the console.
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

    # Print doctrine data
    for doctrine in fleet_count_doctrine:
        print(f"Doctrine Type: {doctrine['doctrine']}, Doctrines Used: {doctrine['doctrine_count']}")

# Example view function calling these methods:
from django.http import HttpResponse

def some_view(request):
    # Call the functions to display the data in the console
    get_fleet_counts()
    get_fleet_count_doctrine()
    return HttpResponse("Fleet counts and doctrine data displayed in the console.")
