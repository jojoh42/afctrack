from django.shortcuts import render
from django.db.models import Count
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from afat.models import FatLink  # Import the FatLink model from afat

@login_required
@permission_required("afctrack.fc_access", raise_exception=True)
def index(request):
    """
    Index view that displays fleet counts per player.
    """
    # Fetch fleet counts using a query similar to `get_fleet_counts`
    fleet_counts = FatLink.objects.values('creator_id')\
                                  .annotate(fleet_count=Count('id'))\
                                  .order_by('-fleet_count')

    # Prepare the context for rendering the template
    context = {
        "text": "Hello, World! 2",
        "fleet_counts": fleet_counts  # Pass the fleet counts to the template
    }

    # Render the template with the context
    return render(request, "afctrack/index.html", context)
