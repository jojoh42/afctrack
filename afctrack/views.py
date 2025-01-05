from django.shortcuts import render
from django.db.models import Count
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from afat.models import FatLink
from django.conf import settings
from datetime import datetime

# Doctrine points
POINTS = {
    'PCT/Roam': 0.5,
    'STR': 1,
    'Hive': 1.5
}

@login_required
@permission_required("afctrack.fc_access", raise_exception=True)
def index(request):
    """
    Index view that displays fleet counts per player.
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
     .order_by('-fleet_count')
    
    # Calculate the total score (points) for all fleets
    total_score = 0

    # Prepare the fleet data with payment information
    fleet_data = []
    for player in fleet_counts:
        player_name = player['creator_id__username']
        fleet_count = player['fleet_count']
        fleet_type = player['fleet_type']

        # Get points for the doctrine
        fleet_points = POINTS.get(fleet_type, 0)

        # Calculate the total score for this fleet
        total_score += fleet_points

        # Add this information to the list
        fleet_data.append({
            'player_name': player_name,
            'fleet_count': fleet_count,
            'fleet_points': fleet_points
        })

    # Fetch the budget from the request
    budget = float(request.GET.get('budget', 3000000000))

    # Calculate ISK per point if the total score is greater than 0
    if total_score > 0:
        isk_per_point = budget / total_score
    else:
        isk_per_point = 0
    
    # Assign payment to each player based on their points
    for fleet in fleet_data:
        fleet['payment'] = fleet['fleet_points'] * isk_per_point

    # Get fleet count per doctrine and type
    fleet_count_doctrine = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('doctrine')\
     .annotate(doctrine_count=Count('id'))\
     .order_by('-doctrine_count')

    fleet_count_type = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('fleet_type')\
     .annotate(type_count=Count('id'))\
     .order_by('-type_count')

    # Prepare the context for rendering the template
    context = {
        "fleet_data": fleet_data,  # Pass the fleet data to the template
        "fleet_count_doctrine": fleet_count_doctrine,  # Fleet count per doctrine
        "fleet_count_type": fleet_count_type  # Fleet count per type
    }

    # Render the template with the context
    return render(request, 'afctrack/index.html', context)
