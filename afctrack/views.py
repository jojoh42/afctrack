import calendar
from datetime import datetime
from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count
from .models import FatLink, Fat

# Doctrine points
POINTS = {
    'PCT/Roam': 0.5,
    'Strat OP': 1,
    'Hive': 1.5
}

def get_fleet_counts_and_payment(budget, selected_month, selected_year):
    """
    Get fleet counts and calculate the payment for each user based on their fleet count, doctrine, and participants.
    Returns a list of dictionaries with player names, payments, and average participants.
    """
    current_month = selected_month
    current_year = selected_year

    # Get the primary keys of users in the "jfc" or "fc" groups
    fc_users_ids = User.objects.filter(groups__name__in=["jfc", "fc"]).values_list('id', flat=True)

    # Filter FatLink by those users and the selected month/year
    fleet_counts = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('creator_id__username', 'id', 'fleet_type')\
     .annotate(fleet_count=Count('id')).order_by('creator_id__username', 'fleet_type')

    # Aggregate fleet counts, doctrine points, and participants
    player_data = {}
    total_fleet_points = 0

    for fleet in fleet_counts:
        player_name = fleet['creator_id__username']
        fleet_id = fleet['id']
        fleet_type = fleet['fleet_type']
        fleet_count = fleet['fleet_count']

        # Count participants for this fleet from the afat_fat table
        participant_count = Fat.objects.filter(fatlink_id=fleet_id).count()

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

def index(request):
    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get the selected month and year from GET parameters, default to current if not provided
    selected_month = int(request.GET.get('month', current_month))
    selected_year = int(request.GET.get('year', current_year))

    # Create a list of months (1 to 12)
    available_months = list(range(1, 13))  # months from 1 to 12

    # Create a list of years (current year and previous 5 years, for example)
    available_years = list(range(current_year - 5, current_year + 1))

    # Get the budget from GET parameters (default to 3 billion ISK)
    budget = int(request.GET.get('budget', 3000000000))

    # Get the fleet counts and payments based on the selected month, year, and budget
    player_payments = get_fleet_counts_and_payment(budget, selected_month, selected_year)

    # Pass data to the template
    context = {
        'month_name': calendar.month_name[selected_month],
        'available_months': available_months,  # List of months
        'available_years': available_years,    # List of years
        'player_payments': player_payments,
        'budget': budget,
        'selected_month': selected_month,  # Ensure selected month is highlighted
        'selected_year': selected_year,    # Ensure selected year is highlighted
    }

    return render(request, 'afctrack/index.html', context)

def doctrine_amount(request):
    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get the selected month and year from GET parameters, default to current if not provided
    selected_month = int(request.GET.get('month', current_month))
    selected_year = int(request.GET.get('year', current_year))

    # Create a list of months (1 to 12)
    available_months = list(range(1, 13))  # months from 1 to 12

    # Create a list of years (current year and previous 5 years, for example)
    available_years = list(range(current_year - 5, current_year + 1))

    # Get the budget from GET parameters (default to 3 billion ISK)
    budget = int(request.GET.get('budget', 3000000000))

    # Get the fleet counts and payments based on the selected month, year, and budget
    player_payments = get_fleet_counts_and_payment(budget, selected_month, selected_year)

    # Pass data to the template
    context = {
        'month_name': calendar.month_name[selected_month],
        'available_months': available_months,  # List of months
        'available_years': available_years,    # List of years
        'player_payments': player_payments,
        'budget': budget,
        'selected_month': selected_month,  # Ensure selected month is highlighted
        'selected_year': selected_year,    # Ensure selected year is highlighted
    }
    return render(request, "afctrack/doctrine_amount.html")