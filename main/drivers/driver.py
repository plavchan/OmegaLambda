import os
import logging

from logger.logger import Logger
from main.observing.observation_run import ObservationRun
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader


def run(folder, obs_ticket, filter):
    
    try: 
        global_config = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))
    except: logging.critical('Could not read or parse config file')
    else: pass

    log_object = Logger()   #I believe this is the only spot where we actually want to instantiate a logger object--everywhere else we can just add messages
    
    try: os.mkdir(folder)   #datetime.datetime.now().strftime('%Y%m%d')
    except: logging.warning('Could not create directory, or directory already exists')
    else: print('New directory for tonight\'s observing has been made!')

    try: json_reader = Reader(obs_ticket)
    except: logging.critical('Error reading observation ticket')

    try: global_filter = ObjectReader(Reader(filter))
    except: logging.critical('Error initializing global filter object')

    try: object_reader = ObjectReader(json_reader)
    except: logging.critical('Error reading observation ticket')
    else: print('Observation ticket has been read.')

    run_object = ObservationRun([object_reader.ticket],
                            r'h:\observatory files\observing sessions\2020_data\{0:s}'.format(folder))
    run_object.observe()
