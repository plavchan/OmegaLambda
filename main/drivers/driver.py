import os
import datetime
import logging

from ...logger.logger import Logger
from ..observing.observation_run import ObservationRun
from ..common.IO.json_reader import Reader
from ..common.IO import config_reader
from ..common.datatype.object_reader import ObjectReader


def run(obs_ticket, datapath=None):
    '''

    Parameters
    ----------
    obs_ticket : STR
        OS filepath to where the observation_ticket files are stored.  Can be anywhere that is accessible.
    data : STR, optional
        Manual save path for data files if you would prefer a manual path rather than the automatic method. The default is None,
        in which case the datapath will be created automatically based on the data_directory parameter in the config file.

    Returns
    -------
    None.

    '''   
    log_object = Logger()   
    # I believe this is the only spot where we actually want to instantiate a logger object--everywhere else we can just add messages
    
    current_path = os.path.abspath(os.path.dirname(__file__))  
    # Gets the current filepath for this driver.py file, to use for automatically finding the config file
    try:
        global_config = ObjectReader(Reader(
            os.path.abspath( os.path.join(current_path, r'../../config/parameters_config.json') )))
    except: logging.critical('Could not read or parse config file')

    try: global_filter = ObjectReader(Reader(
            os.path.abspath( os.path.join(current_path, r'../../config/fw_config.json') )))
    except: logging.critical('Error initializing global filter object')
    
    config_dict = config_reader.get_config()
    
    try:
        if datapath:
            folder = r'{}'.format(datapath)     # Reads as a raw string
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
