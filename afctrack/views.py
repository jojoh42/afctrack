from django.shortcuts import render
from django.db.models import Count
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from afat.models import FatLink, Fat
from datetime import datetime
from calendar import month_name

# Doctrine points
POINTS = {
    'PCT/Roam': 0.5,
    'Strat OP': 1,
    'Hive': 1.5
}

@login_required
@permission_required("afctrack.fc_access", raise_exception=True)
def index(request):
    """
    Index view that displays fleet counts per player and includes a month/year selector.
    """
    # Get the selected month and year, or default to the current month and year
    selected_month = int(request.GET.get('month', datetime.now().month))
    selected_year = int(request.GET.get('year', datetime.now().year))

    # Get a list of available months and years for the dropdown
    available_months = list(range(1, 13))  # January (1) to December (12)
    current_year = datetime.now().year
    available_years = list(range(current_year - 5, current_year + 1))  # Last 5 years to the current year

    # Create a dictionary for month names
    month_names = {i: month_name[i] for i in range(1, 13)}

    # Get the primary keys of users in the "jfc" or "fc" groups
    fc_users_ids = User.objects.filter(groups__name__in=["jfc", "fc"]).values_list('id', flat=True)

    # Filter FatLink by those users and the selected month/year
    fleet_counts = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=selected_month,
        created__year=selected_year
    ).values('creator_id__username', 'id', 'fleet_type')\
     .annotate(
        fleet_count=Count('id')
    ).order_by('creator_id__username', 'fleet_type')

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
    budget = int(request.GET.get('budget', 3000000000))
    if total_fleet_points > 0:
        isk_per_point = budget / total_fleet_points
        round_isk_per_point = round(isk_per_point)
    else:
        isk_per_point = 0
        round_isk_per_point = round(isk_per_point)

    # Calculate the payment for each player
    for player_name, data in player_data.items():
        # Calculate the payment based on the doctrine points
        data['payment'] = data['total_fleet_points'] * round_isk_per_point
        # Calculate the average participants per fleet
        data['avg_participants'] = data['total_participants'] / data['total_fleet_count'] if data['total_fleet_count'] > 0 else 0

    # Prepare the context for rendering the template
    context = {
        "player_data": player_data,  # Pass the aggregated player data to the template
        "available_months": available_months,
        "available_years": available_years,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "month_names": month_names,  # Pass the month names to the template
    }

    # Render the template with the context
    return render(request, 'afctrack/index.html', context)
