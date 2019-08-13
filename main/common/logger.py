import logging

# DEBUG: Detailed info, typically used for diagnosing problems
# INFO: Confirmation that things are working as expected
# WARNING: Something unexpected happened or problem in near future
# ERROR: More serious problem
# CRITICAL: Very Serious error

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler = logging.FileHandler('C:\\Users\\Nicholas Pepin\\Desktop\\CameraErrorLog.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info("logger.py works")
    
