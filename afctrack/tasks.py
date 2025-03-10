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
    import logging
    import sys  # ✅ Um in die Konsole zu schreiben

    logger = logging.getLogger(__name__)

    # ✅ Logge Fortschritt in **die Django-Konsole** und nicht nur in Celery
    print("✅ Celery-Task gestartet mit Daten:", session_data, file=sys.stdout)
    sys.stdout.flush()

    time.sleep(20)

    from afctrack.views import update_fleet_motd

    print("🚀 Aufruf von update_fleet_motd", file=sys.stdout)
    sys.stdout.flush()

    # 🛠 Erstelle DummyRequest für Django-View
    class DummyRequest:
        session = session_data  # Simulierter Request

    result = update_fleet_motd(DummyRequest(), None)

    print("✅ update_fleet_motd abgeschlossen mit Result:", result, file=sys.stdout)
    sys.stdout.flush()

    return result

