from django.contrib.sessions.backends.db import SessionStore
import logging
import time
from celery import shared_task

logger = logging.getLogger(__name__)

@shared_task
def delayed_updated_fleet_motd(session_data):
    """Updates the MOTD for the fleet after a delay."""
    import logging
    logger = logging.getLogger(__name__)

    logger.warning("🚀 Celery-Task gestartet mit Daten: %s", session_data)

    from django.contrib.auth.models import AnonymousUser
    from afctrack.views import update_fleet_motd

    class DummyRequest:
        session = session_data
        user = AnonymousUser()  # Fake-User hinzufügen

    logger.warning("🚀 Aufruf von update_fleet_motd mit DummyRequest")

    result = update_fleet_motd(DummyRequest(), None)  # Token bleibt None

    logger.warning("✅ update_fleet_motd abgeschlossen mit Result: %s", result)

    return result

