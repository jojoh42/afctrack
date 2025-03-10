"""App Tasks"""

# Standard Library
import logging

# Third Party
from celery import shared_task

logger = logging.getLogger(__name__)

# Create your tasks here


# Example Task
@shared_task
def example_task():
    """Example Task"""

    pass

@shared_task
def delayed_updated_fleet_motd(request_data):
    """Updates the MOTD for the fleet after a delay."""
    time.sleep(20)
    from .views import update_fleet_motd
    return update_fleet_motd(request_data, None)  # Token muss ggf. separat übergeben werden
