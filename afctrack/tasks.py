from django.contrib.sessions.backends.db import SessionStore
import logging
import time
from celery import shared_task

logger = logging.getLogger(__name__)

@shared_task
def delayed_updated_fleet_motd(session_data):
    """Updates the MOTD for the fleet after a delay."""
    
    logger.warning("🚀 Celery-Task gestartet mit Daten: %s", session_data)
    
    time.sleep(20)
    
    from afctrack.views import update_fleet_motd

    # Simuliere eine Django Request-Session
    class DummyRequest:
        def __init__(self, session_data):
            self.session = SessionStore()
            self.session.update(session_data)  # Speichert das dict als echte Session
    
    request = DummyRequest(session_data)

    logger.warning("🚀 Aufruf von update_fleet_motd")

    result = update_fleet_motd(request, None)  # Token ist None, weil Celery es nicht kennt

    logger.warning("✅ update_fleet_motd abgeschlossen mit Result: %s", result)

    return result
