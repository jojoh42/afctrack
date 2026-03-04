from django.contrib.sessions.backends.db import SessionStore
import logging
import time
from celery import shared_task
from django.contrib.auth.models import User
from esi.models import Token

logger = logging.getLogger(__name__)

@shared_task
def delayed_updated_fleet_motd(user_id, session_data):
    """Updates the MOTD for the fleet after a delay."""
    
    # Import hier, um Zirkuläre Imports zu vermeiden
    from afctrack.views import set_fleet_motd

    logger.info(f"🚀 Celery-Task gestartet für User ID {user_id} mit Daten: {session_data}")

    try:
        user = User.objects.get(id=user_id)
        
        # Suche einen gültigen Token für den User mit Schreibrechten
        token = Token.objects.filter(
            user=user,
            scopes__name='esi-fleets.write_fleet.v1'
        ).first()

        if not token:
            logger.error(f"❌ Kein gültiger Token mit Scope 'esi-fleets.write_fleet.v1' für User {user} gefunden.")
            return

        # Rufe die Logik direkt auf (ohne Request-Objekt)
        set_fleet_motd(
            token=token,
            fleet_boss=session_data.get('fleet_boss'),
            doctrine_name=session_data.get('doctrine_name'),
            comms=session_data.get('comms'),
            base_url=session_data.get('base_url')
        )

    except User.DoesNotExist:
        logger.error(f"❌ User mit ID {user_id} nicht gefunden.")
    except Exception as e:
        logger.exception(f"❌ Unerwarteter Fehler im Task: {e}")
