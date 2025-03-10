"""App Tasks"""

# Standard Library
import logging
import time
# Third Party
from celery import shared_task

# Logger auf die richtige Datei setzen
logger = logging.getLogger("afctrack")
file_handler = logging.FileHandler("/mnt/c/Users/helol/Documents/Codes/aa-dev-2/aa-dev/myauth/log/extension.log")
formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s]: %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)


@shared_task
def example_task():
    """Example Task"""
    logger.info("Beispiel Celery-Task wurde gestartet.")
    pass


@shared_task
def delayed_updated_fleet_motd(session_data):
    """Updates the MOTD for the fleet after a delay."""
    
    logger.info("🎯 Celery-Task gestartet mit Daten: %s", session_data)

    # 20-Sekunden-Countdown mit Logging
    for i in range(20, 0, -1):
        logger.info(f"⏳ Countdown: {i} Sekunden bis zur MOTD-Aktualisierung...")
        time.sleep(1)

    logger.info("🚀 Countdown beendet. update_fleet_motd wird nun aufgerufen.")

    from afctrack.views import update_fleet_motd

    # Simuliere eine Request-Session für die Funktion
    class DummyRequest:
        session = session_data

    result = update_fleet_motd(DummyRequest(), None)

    logger.info("✅ update_fleet_motd abgeschlossen mit Result: %s", result)

    return result
