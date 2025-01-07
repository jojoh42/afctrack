from django.shortcuts import render
from django.db.models import Count
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from afat.models import FatLink
from datetime import datetime

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
    Main view that fetches fleet data and renders it on the template.
    """
    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get the primary keys of users in the "jfc" or "fc" groups
    fc_users_ids = User.objects.filter(groups__name__in=["jfc", "fc"]).values_list('id', flat=True)

    # Fetch fleet count per player
    fleet_counts = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('creator_id__username')\
     .annotate(fleet_count=Count('id'))\
     .order_by('-fleet_count')

    # Fetch doctrine counts
    doctrine_counts = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('doctrine')\
     .annotate(doctrine_count=Count('id'))\
     .order_by('-doctrine_count')

    # Fetch fleet type counts
    type_counts = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('fleet_type')\
     .annotate(type_count=Count('id'))\
     .order_by('-type_count')

    # Pass data to the template
    context = {
        "fleet_counts": fleet_counts,
        "doctrine_counts": doctrine_counts,
        "type_counts": type_counts,
    }
    return render(request, 'afctrack/index.html', context)
