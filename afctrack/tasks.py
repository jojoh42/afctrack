"""App Tasks"""

# Standard Library
import logging
import time
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
def delayed_updated_fleet_motd(session_data):
    """Updates the MOTD for the fleet after a delay, mit Debug-Output."""

    import logging
    logger = logging.getLogger(__name__)

    logger.info("Celery-Task gestartet mit Daten: %s", session_data)

    countdown = 20
    for i in range(countdown, 0, -1):
        logger.info(f"Countdown: {i} Sekunden bis zur MOTD-Aktualisierung...")
        time.sleep(1)  # Warte eine Sekunde

    logger.info("Countdown beendet. update_fleet_motd wird nun aufgerufen.")

    from afctrack.views import update_fleet_motd

    # Simuliere eine Django-Request-Session für die Funktion
    class DummyRequest:
        session = session_data

    result = update_fleet_motd(DummyRequest(), None)

    logger.info("update_fleet_motd abgeschlossen mit Result: %s", result)

    return result

