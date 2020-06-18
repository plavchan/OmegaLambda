from main.observing.observation_run import ObservationRun
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader
import datetime
import os
import logging
from logger.logger import Logger

try: 
    global_config = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))
except: logging.critical('Could not read or parse config file')
else: pass

log_object = Logger()   #I believe this is the only spot where we actually want to instantiate a logger object--everywhere else we can just add messages

folder = datetime.datetime.now().strftime('%Y%m%d')
try: 
    os.mkdir(os.path.join(global_config.ticket.data_directory, folder))
except: logging.warning('Could not create directory, or directory already exists')
else: logging.info('New directory for tonight\'s observing has been made!')

try: json_reader = Reader(os.path.join(global_config.ticket.home_directory, r'test\test.json'))
except: logging.critical('Could not read observation ticket.')
else: logging.info('Observation ticket has been read')

try: global_filter = ObjectReader(Reader(os.path.join(global_config.ticket.home_directory, r'config\fw_config.json')))
except: logging.critical('Error initializing global filter object')
else: pass

try: object_reader = ObjectReader(json_reader)
except: logging.critical('Could not parse observation ticket.')
else: logging.info('Observation ticket has been parsed')

run_object = ObservationRun([object_reader.ticket],
                            os.path.join(global_config.ticket.data_directory, folder))
run_object.observe()