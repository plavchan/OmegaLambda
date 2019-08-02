import logging
from main.common import cAmera
from main.common.cAmera import *


# DEBUG: Detailed info, typically used for diagnosing problems
# INFO: Confirmation that things are working as expected
# WARNING: Something unexpected happened or problem in near future
# ERROR: More serious problem
# CRITICAL: Very Serious error

class Logger(Camera):
    # logging.basicConfig(filename="C:\\Users\\Nicholas Pepin\\Desktop\\CameraErrorLog.log", level=logging.DEBUG, filemode='w', format="%(asctime)s - %(levelname)s - %(message)s")
    # logger = logging.getLogger()  #These two lines contain a scrunched version of below but without handlers

    # Creates 'cAmera' logger
    logger = logging.getLogger('cAmera')
    logger.setLevel(logging.DEBUG)
    # creates filehandlers
    fh = logging.FileHandler('C:\\Users\\Nicholas Pepin\\Desktop\\CameraErrorLog.log')
    fh.setLevel(logging.DEBUG)
    # Creates console logger for higher level logging
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    # Creates Formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # adds handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info('Camera process has started')
    # Creating a link to Camera()
    logger.info('Created an instance of Camera log')
    logger.info('Collecting Camera logging information')
    a = cAmera.Camera('camera_work')        #idk why 'a' from the 'def log()' function does not transfer over. Need help
    a.log()                                 #supposed to run log() and have a returned
    
