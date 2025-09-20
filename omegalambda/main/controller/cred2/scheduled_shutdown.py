# Script for automating shutting down the observatory
# without running omegalambda.
#######################
SHUTDOWN_TIME = "04:45"
KILL_PYTHON_PROCESSES = True
TAKE_CALIBRATION_IMAGES = True
#######################

import win32com.client
from datetime import datetime, timedelta
from time import sleep
import logging
import pywintypes
import sys
import psutil
import os

from take_calibration_images import take_calibration_images


DOME_OPEN = 0
DOME_CLOSED = 1
DOME_OPENING = 2
DOME_CLOSING = 3
DOME_ERROR = 4
ERROR = 5

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def dome_connect():
    DOME.Connected = True
    logging.info("Dome connected.")

def dome_status():
    try:
        return DOME.ShutterStatus
    except Exception as e:
        logging.error(f"Error getting dome status: {e}")
    return ERROR

def dome_close():
    try:
        DOME.CloseShutter()
    except Exception as e:
        logging.error(f"Error closing dome: {e}")
        return False
    logging.info("Dome is closing.")

def await_dome_closed():
    while dome_status() == DOME_CLOSING:
        print('.', end='', flush=True)
        sleep(2)

    if dome_status() != DOME_CLOSED:
        logging.error(f"Dome did not close properly. Dome status: {dome_status()}")
        return False
    
    logging.info("Dome is closed.")
    return True

def dome_park():
    try:
        DOME.Slaved = False
        DOME.Park()
    except Exception as e:
        logging.error(f"Error parking dome: {e}")
    logging.info("Dome is parking.")

def telescope_connect():
    TELESCOPE.SlewSettleTime = 1
    TELESCOPE.Connected = True
    logging.info("Telescope connected.")

def telescope_park():
    tries = 0
    try:
        while TELESCOPE.Tracking and tries < 5:
            try:
                TELESCOPE.Tracking = False
            except (AttributeError, pywintypes.com_error) as e:
                logging.error(f"Error disabling telescope tracking: {e}")
            sleep(5)
            tries += 1
        if tries >= 5:
            logging.error("Failed to disable telescope tracking after 5 attempts.")
        if not TELESCOPE.AtPark:
            TELESCOPE.Park()
    except Exception as e:
        logging.error(f"Error parking telescope: {e}")
    logging.info("Telescope is parking.")

def kill_python_procs():
    logging.info("Killing all Python processes.")
    my_pid = os.getpid()
    procs_to_kill = [p for p in psutil.process_iter() if p.pid != my_pid and 'python' in p.name().lower()]
    for proc in procs_to_kill:
        try:
            proc.terminate()
            proc.wait(timeout=120)
            logging.info(f"Killed Python process with PID {proc.pid}.")
        except psutil.NoSuchProcess:
            logging.warning(f"Process with PID {proc.pid} does not exist.")
        except psutil.TimeoutExpired:
            logging.error(f"Process with PID {proc.pid} did not terminate in time. Attempting to kill it.")
            proc.kill()
        except Exception as e:
            logging.error(f"Error killing Python process with PID {proc.pid}: {e}")

def shutdown():
    logging.info("Shutting down observatory.")
    dome_close()
    sleep(5)
    dome_park()
    sleep(5)
    telescope_park()

    sleep(2 * 60)

    tries = 0
    while not await_dome_closed() and tries <= 5:
        logging.error("Dome did not close properly. Retrying in 60 seconds.")
        tries += 1
        sleep(60)

    if KILL_PYTHON_PROCESSES:
        kill_python_procs()

    logging.info("Shutdown complete.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        SHUTDOWN_TIME = sys.argv[1]

    if len(sys.argv) > 2:
        KILL_PYTHON_PROCESSES = sys.argv[2].lower().strip() in ('true', 'yes', '1')

    if len(sys.argv) > 3:
        TAKE_CALIBRATION_IMAGES = sys.argv[3].lower().strip() in ('true', 'yes', '1')

    SHUTDOWN_TIME = datetime.strptime(SHUTDOWN_TIME, "%H:%M").time()
    shutdown_date = datetime.now().date() if datetime.now().time() < SHUTDOWN_TIME else datetime.now().date() + timedelta(days=1)
    SHUTDOWN_DATETIME = datetime.combine(shutdown_date, SHUTDOWN_TIME)

    logging.info(f"Shutdown scheduled for {SHUTDOWN_DATETIME}.")

    DOME = win32com.client.Dispatch("ASCOMDome.Dome")
    dome_connect()

    TELESCOPE = win32com.client.Dispatch("ASCOM.SoftwareBisque.Telescope")
    telescope_connect()

    sleep_seconds = SHUTDOWN_DATETIME.timestamp() - datetime.now().timestamp()
    logging.info(f"Sleeping for {int(sleep_seconds)} seconds before shutdown.")
    sleep(sleep_seconds)
    shutdown()

    if TAKE_CALIBRATION_IMAGES:
        sleep(10)
        take_calibration_images()