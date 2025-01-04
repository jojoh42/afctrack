from django.db import models
from django.db.models import Count
from afat.models import FatLink  # Import the FatLink model from afat

class General(models.Model):
    """Meta model for app permissions"""
    class Meta:
        """Meta definitions"""
        managed = False
        default_permissions = ()
        permissions = (
            ("manage_afctrack", "Can manage the afctrack APP"),
            ("jfc_access", "Can see his own Information"),
            ("fc_access", "Can see the Activity of every FC and JFC"),
        )
        verbose_name = "afctrack"
    
class MonthlyFCPayment(models.Model):
    character_id = models.IntegerField(verbose_name="Character ID", blank=False)
    month = models.IntegerField(verbose_name="Taxed month", blank=False, default=0)
    year = models.IntegerField(verbose_name="Taxed year", blank=False, default=0)
    player_name = models.IntegerField(verbose_name="Player Name", blank=False)
    payment_value = models.IntegerField(verbose_name="Payment Amount", blank=False, default=0)
    fleet_amount = models.IntegerField(verbose_name="Fleet Amount", blank=False, default=0)

# Refactor the query into a function that is called after models are loaded
def get_fleet_counts():
    fleet_counts = FatLink.objects.values('creator_id')\
                                   .annotate(fleet_count=Count('id'))\
                                   .order_by('-fleet_count')

    for player in fleet_counts:
        print(f"Creator ID: {player['creator_id']}, Fleets Created: {player['fleet_count']}")

# You can call this function in a view or another part of your application
# For example, if you're doing it in a view:
# from django.http import HttpResponse
# def some_view(request):
#     get_fleet_counts()
#     return HttpResponse("Fleet counts displayed in the console")
