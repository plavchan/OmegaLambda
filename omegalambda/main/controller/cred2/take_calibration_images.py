# Script for automating taking calibration images with the NIR camera.
#######################
NUM_CALIBRATION_IMAGES: int = 15  # Number of calibration images to take
EXPTIME: float = 90.0  # Exposure time in seconds for calibration images
#######################
from datetime import datetime, timedelta
from time import sleep
import logging
import os

from flatfield_lamp import FlatLamp
from tertiary_mirror import TertiaryMirror
from camera import NIRCamera


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def take_flats():
    logging.info("Taking flats...")
    flatlamp.turn_on()
    tertiary_mirror.select_camera("NIR")
    sleep(5)
    camera.start_exposing(
        exposure_time=EXPTIME,
        save_dir=save_dir,
        name="Flat",
    )
    flatlamp.turn_off()
    sleep(5)
    logging.info("Done taking flats.")


def take_darks():
    logging.info("Taking darks...")
    tertiary_mirror.select_camera("CCD")
    sleep(5)
    camera.start_exposing(
        exposure_time=EXPTIME,
        save_dir=save_dir,
        name="Dark",
    )
    sleep(5)
    logging.info("Done taking darks.")

##############

date = datetime.now().date() if datetime.now().hour < 12 else datetime.now().date() + timedelta(days=1)
date = date.strftime("%Y%m%d")
save_dir = os.path.join("H:/Observatory Files/Observing Sessions/2025_Data", date)

##############

camera = NIRCamera()
camera.start()
camera.check_connection()
flatlamp = FlatLamp()
flatlamp.start()
flatlamp.check_connection()
tertiary_mirror = TertiaryMirror()
tertiary_mirror.start()
tertiary_mirror.check_connection()

sleep(30)

##############

logging.info(f"Taking {NUM_CALIBRATION_IMAGES} darks and flats at {EXPTIME} seconds exposure time.")

take_darks()
take_flats()

##############

camera.disconnect()
flatlamp.disconnect()
tertiary_mirror.disconnect()
logging.info("Calibration images taken successfully.")