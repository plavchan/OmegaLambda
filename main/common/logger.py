import logging
from main.common import cAmera
from main.common.cAmera import *


# DEBUG: Detailed info, typically used for diagnosing problems
# INFO: Confirmation that things are working as expected
# WARNING: Something unexpected happened or problem in near future
# ERROR: More serious problem
# CRITICAL: Very Serious error


class main:
    # logging.basicConfig(filename="C:\\Users\\Nicholas Pepin\\Desktop\\CameraErrorLog.log", level=logging.DEBUG,
    # filemode='w', format="%(asctime)s - %(levelname)s - %(message)s") logger = logging.getLogger()  #These two
    # lines contain a scrunched version of below but without handlers
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
    logger = logging.getLogger()
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)

    logger.info('Camera process has started : ' + __name__)
    cAmera.Camera.log()  # need to fulfil self

    # Theoretically, it works. but in 'cAmera.Camera.log()' it says that self needs to be fulfilled
    # and I have no idea how to do that. If someone could help guide me to a paper or video that would
    # explain it, that would be very helpful.
    
