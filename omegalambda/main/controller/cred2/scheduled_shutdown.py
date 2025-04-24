shutdown_time = "06:00"
#######################


import win32com.client
from datetime import datetime, timedelta
from time import sleep
import logging


shutdown_time = datetime.strptime(shutdown_time, "%H:%M").time()
shutdown_date = datetime.now().date() if datetime.now().time() < shutdown_time else datetime.now().date() + timedelta(days=1)
SHUTDOWN_DATETIME = datetime.combine(shutdown_date, shutdown_time)
LOGGER = logging.getLogger(__name__)

LOGGER.info(f"Shutdown scheduled for {SHUTDOWN_DATETIME}.")

DOME = win32com.client.Dispatch("ASCOMDome.Dome")
TELESCOPE = win32com.client.Dispatch("ASCOMTelescope.Telescope")

DOME_OPEN = 0
DOME_CLOSED = 1
DOME_OPENING = 2
DOME_CLOSING = 3
DOME_ERROR = 4
ERROR = 5


def dome_status():
    try:
        return DOME.ShutterStatus
    except Exception as e:
        LOGGER.error(f"Error getting dome status: {e}")
    return ERROR

def dome_close():
    try:
        DOME.CloseShutter()
    except Exception as e:
        LOGGER.error(f"Error closing dome: {e}")
        return False
    LOGGER.info("Dome is closing.")

def await_dome_closed():
    while dome_status() == DOME_CLOSING:
        print('.', end='', flush=True)
        sleep(2)

    if dome_status() != DOME_CLOSED:
        LOGGER.error(f"Dome did not close properly. Dome status: {dome_status()}")
        return False
    
    LOGGER.info("Dome is closed.")
    return True

def dome_park():
    try:
        DOME.Park()
    except Exception as e:
        LOGGER.error(f"Error parking dome: {e}")
    LOGGER.info("Dome is parking.")

def telescope_park():
    try:
        if not TELESCOPE.AtPark:
            TELESCOPE.Park()
    except Exception as e:
        LOGGER.error(f"Error parking telescope: {e}")
    LOGGER.info("Telescope is parking.")

def shutdown():
    LOGGER.info("Shutting down observatory.")
    dome_close()
    sleep(2)
    telescope_park()
    sleep(2)
    dome_park()
    sleep(2)

    tries = 0
    while not await_dome_closed() and tries <= 5:
        LOGGER.error("Dome did not close properly. Retrying in 60 seconds.")
        sleep(60)

    LOGGER.info("Shutdown complete.")

sleep_seconds = SHUTDOWN_DATETIME.timestamp() - datetime.now().timestamp()
LOGGER.info("Sleeping for {sleep_seconds} seconds before shutdown.")
sleep(sleep_seconds)
shutdown()