import os
import datetime
import logging

from ...logger.logger import Logger
from ..observing.observation_run import ObservationRun
from ..common.IO.json_reader import Reader
from ..common.IO import config_reader
from ..common.datatype.object_reader import ObjectReader


def run(obs_ticket, data=None, config=None, filter=None, logger=None):
    '''

    Parameters
    ----------
    obs_ticket : STR
        OS filepath to where the observation_ticket files are stored.  Can be anywhere that is accessible.
    data : STR, optional
        Manual save path for data files if you would prefer a manual path rather than the automatic method. The default is None,
        in which case the data path will be created automatically based on the data_directory parameter in the config file.
    config : STR, optional
        Manual save path for the general configuration json file.  The default is None, in which case the config path will be the
        default for this code, under -omegalambda/config.
    filter : STR, optional
        Manual save path for the filter wheel configuration json file.  The default is None, in which case the filter wheel path will
        be the default for this code, under -omegalambda/config.
    logger : STR, optional
        Manual save path for the logging configuration file.  The default is None, in which case the logging path will be the default
        for this code, under -omegalambda/config.

    Returns
    -------
    None.

    '''
    current_path = os.path.abspath(os.path.dirname(__file__))
   # Gets the current filepath for this driver.py file, to use for automatically finding the config files
    
    if logger:
        log_object = Logger(logger)
    else:
        path = os.path.abspath( os.path.join(current_path, r'../../config/logging.json'))
        log_object = Logger(path)
    # I believe this is the only spot where we actually want to instantiate a logger object--everywhere else we can just add messages
    
    try:
        if config:
            global_config = ObjectReader(Reader(config))
        else:
            global_config = ObjectReader(Reader(
                os.path.abspath( os.path.join(current_path, r'../../config/parameters_config.json') )))
    except: logging.critical('Could not read or parse config file')

    try: 
        if filter:
            global_filter = ObjectReader(Reader(filter))
        else:
            global_filter = ObjectReader(Reader(
                os.path.abspath( os.path.join(current_path, r'../../config/fw_config.json') )))
    except: logging.critical('Error initializing global filter object')
    
    config_dict = config_reader.get_config()
    
    try:
        if data:
            folder = r'{}'.format(data)     # Reads as a raw string
        else:
            folder = os.path.join(config_dict.data_directory, datetime.datetime.now().strftime('%Y%m%d'))
        os.mkdir(folder)
    except: logging.warning('Could not create directory, or directory already exists')
    else: print('New directory for tonight\'s observing has been made!')

    try: object_reader = ObjectReader(Reader(obs_ticket))
    except: logging.critical('Error reading observation ticket')
    else: print('Observation ticket has been read.')

    run_object = ObservationRun([object_reader.ticket], folder)
    run_object.observe()
