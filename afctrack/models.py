from itertools import count
from django.db import models
from django.db.models import Count  # Import Count from django.db.models
# Import the FatLink model from the afat project
from afat.models import FatLink  # Correctly import FatLink model from the afat project

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

# Query directly from the FatLink model to get fleet counts for each creator_id
fleet_counts = FatLink.objects.values('creator_id')\
                               .annotate(fleet_count=Count('id'))\
                               .order_by('-fleet_count')

# Print the results
for player in fleet_counts:
    print(f"Creator ID: {player['creator_id']}, Fleets Created: {player['fleet_count']}")
