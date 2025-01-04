"""App Views"""

# Django
from django.contrib.auth.decorators import login_required, permission_required
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render
from .models import AtatFatlink
from django.db.models import Count

@login_required
@permission_required("afctrack.fc_access")
def index(request: WSGIRequest) -> HttpResponse:
    """
    Index view that displays fleet counts per player.
    :param request:
    :return:
    """
    
    # Query to get fleet counts per player
    fleet_counts = AtatFatlink.objects.values('creator_id')\
                                       .annotate(fleet_count=Count('fleet_id'))\
                                       .order_by('-fleet_count')

    # Pass the fleet counts to the context
    context = {
        "text": fleet_counts  # Add fleet counts to the context
    }

    return render(request, "afctrack/index.html", context)

