from django.db import models
from django.db.models import Count
from django.contrib.auth.models import User
from afat.models import FatLink
from django.conf import settings
from datetime import datetime

# Get payment amounts from settings (default to specified values if not found)
FC_PAYMENT_AMOUNT = getattr(settings, "FC_Payment_Ammount", 200000000)
FC_PAYMENT_MAX = getattr(settings, "FC_Payment_Ammount_Max", 1000000000)
JFC_PAYMENT_AMOUNT = getattr(settings, "JFC_Payment_Ammount", 100000000)
JFC_PAYMENT_MAX = getattr(settings, "JFC_Payment_Ammount_Max", 500000000)


def get_fleet_counts_and_payment():
    """
    Get fleet counts and calculate payments for users in "jfc" or "fc" groups.
    Returns a list of dictionaries with player names, fleet counts, and payment amounts.
    """
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get IDs of users in the "jfc" or "fc" groups
    fc_user_ids = User.objects.filter(groups__name__in=["jfc", "fc"]).values_list('id', flat=True)

    # Query FatLink for fleets created by those users in the current month/year
    fleet_counts = (
        FatLink.objects.filter(
            creator_id__in=fc_user_ids,
            created__month=current_month,
            created__year=current_year
        )
        .values('creator__username')
        .annotate(fleet_count=Count('id'))
        .order_by('-fleet_count')
    )

    # Calculate payments for each user
    player_payments = []
    for player in fleet_counts:
        player_name = player['creator__username']
        fleet_count = player['fleet_count']

        # Determine user group (FC or JFC) and respective payment rates
        user = User.objects.get(username=player_name)
        if user.groups.filter(name="fc").exists():
            base_payment = FC_PAYMENT_AMOUNT
            max_payment = FC_PAYMENT_MAX
        else:
            base_payment = JFC_PAYMENT_AMOUNT
            max_payment = JFC_PAYMENT_MAX

        # Calculate total payment, capped by the max payment amount
        payment_per_fleet = base_payment * fleet_count if fleet_count > 0 else 0
        final_payment = min(payment_per_fleet, max_payment)

        player_payments.append({
            'player_name': player_name,
            'fleet_count': fleet_count,
            'payment': final_payment
        })

    return player_payments


def get_fleet_count_by_doctrine():
    """
    Get the count of fleets grouped by doctrine for the current month/year.
    Returns a list of dictionaries with doctrine names and fleet counts.
    """
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get IDs of users in the "jfc" or "fc" groups
    fc_user_ids = User.objects.filter(groups__name__in=["jfc", "fc"]).values_list('id', flat=True)

    # Query FatLink for doctrine counts
    doctrine_counts = (
        FatLink.objects.filter(
            creator_id__in=fc_user_ids,
            created__month=current_month,
            created__year=current_year
        )
        .values('doctrine')
        .annotate(doctrine_count=Count('id'))
        .order_by('-doctrine_count')
    )

    return doctrine_counts


def get_fleet_count_by_type():
    """
    Get the count of fleets grouped by fleet type for the current month/year.
    Returns a list of dictionaries with fleet types and fleet counts.
    """
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get IDs of users in the "jfc" or "fc" groups
    fc_user_ids = User.objects.filter(groups__name__in=["jfc", "fc"]).values_list('id', flat=True)

    # Query FatLink for fleet type counts
    type_counts = (
        FatLink.objects.filter(
            creator_id__in=fc_user_ids,
            created__month=current_month,
            created__year=current_year
        )
        .values('fleet_type')
        .annotate(type_count=Count('id'))
        .order_by('-type_count')
    )

    return type_counts
