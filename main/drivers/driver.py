import os
import logging
import re
from json.decoder import JSONDecodeError

from ...logger.logger import Logger
from ..observing.observation_run import ObservationRun
from ..common.IO.json_reader import Reader
from ..common.IO import config_reader
from ..common.datatype.object_reader import ObjectReader


def run(obs_tickets, data=None, config=None, _filter=None, logger=None, shutdown=None, calibration=None):
    """

    Parameters
    ----------
    obs_tickets : LIST
        OS filepath to where each observation ticket is stored, or a single path to the directory of observation
        tickets. Can be anywhere that is accessible.
    data : STR, optional
        Manual save path for data files if you would prefer a manual path rather than the automatic method. The default
        is None, in which case the data path will be created automatically based on the data_directory parameter in the
        config file.
    config : STR, optional
        Manual save path for the general configuration json file.  The default is None, in which case the config path
        will be the default for this code, under -omegalambda/config.
    _filter : STR, optional
        Manual save path for the filter wheel configuration json file.  The default is None, in which case the filter
        wheel path will be the default for this code, under -omegalambda/config.
    logger : STR, optional
        Manual save path for the logging configuration file.  The default is None, in which case the logging path will
        be the default for this code, under -omegalambda/config.
    shutdown : BOOL, optional
        Toggle to shut down the observatory after running tickets.  The default in None, in which case True will be
        passed in via argparse, so the observatory will shut down.
    calibration : BOOL, optional
        Toggle to take calibration images or not.  The default is None, in which case True will be passed in via
        argparse, so the observatory will take darks and flats at the specified time in the config file.

    Returns
    -------
    None.

    """
    current_path = os.path.abspath(os.path.dirname(__file__))
    # Gets the current filepath for this driver.py file, to use for automatically finding the config files
    config_path = os.path.join(current_path, r'..', r'..', r'config')
    
    if logger:
        log_object = Logger(logger)
    else:
        path = os.path.abspath(os.path.join(config_path, r'logging.json'))
        log_object = Logger(path)
    # I believe this is the only spot where we actually want to instantiate a logger object
    # everywhere else we can just add messages
    
    try:
        if config:
            global_config = ObjectReader(Reader(config))
        else:
            global_config = ObjectReader(Reader(
                os.path.abspath(os.path.join(config_path, r'parameters_config.json'))))
    except (JSONDecodeError, FileNotFoundError):
        logging.critical('Config file either could not be found or could not be parsed')
        return

    try: 
        if _filter:
            global_filter = ObjectReader(Reader(_filter))
        else:
            global_filter = ObjectReader(Reader(
                os.path.abspath(os.path.join(config_path, r'fw_config.json'))))
    except (JSONDecodeError, FileNotFoundError):
        logging.critical('FilterWheel config file either could not be found or could not be parsed')
        return
    
    config_dict = config_reader.get_config()

    if os.path.isfile(obs_tickets[0]):
        observation_request_list = [ticket_object for ticket in obs_tickets
                                    if (ticket_object := read_ticket(ticket))]
    else:
        observation_request_list = [ticket_object for filename in os.listdir(obs_tickets[0])
                                    if (ticket_object := read_ticket(os.path.join(obs_tickets[0], filename)))]

    observation_request_list.sort(key=start_time)
    if data:
        folder = [r'{}'.format(data)]  # Reads as a raw string
    else:
        folder = [os.path.join(config_dict.data_directory, ticket.start_time.strftime('%Y%m%d'), ticket.name)
                  for ticket in observation_request_list]
    if len(folder) != len(observation_request_list):
        raise ValueError('The length of tickets does not match with the length of folders...something has gone wrong.')

    for fol in folder:
        if not os.path.exists(fol):
            os.makedirs(fol)
        else:
            logging.debug('Folder already exists: {:s}'.format(fol))
    logging.info('New directories for tonight\'s observing have been made!')
        
    run_object = ObservationRun(observation_request_list, folder, shutdown, calibration)
    run_object.observe()

    log_object.stop()


def read_ticket(ticket):
    """

    Parameters
    ----------
    ticket : STR
        Path to ticket json file.

    Returns
    -------
    CLASS INSTANCE OBJECT of ObservationTicket
        Observation Ticket object to be read by observation_run.py.

    """
    if not os.path.isfile(ticket):
        logging.critical('Invalid file path to observation ticket')
        return None
    try:
        object_reader = ObjectReader(Reader(ticket))
    except AttributeError:
        logging.critical('Error reading observation ticket')
        return
    else:
        print('Observation ticket has been read')
        return object_reader.ticket


def start_time(ticket_object):
    """

    Parameters
    ----------
    ticket_object : CLASS INSTANCE OBJECT of ObservationTicket
        Created by observation_ticket.

    Returns
    -------
    DATETIME.DATETIME
        Datetime object for the ticket's start time.  Used to sort the tickets by start time.

    """
    return ticket_object.start_time


def alphanumeric_sort(_list):
    """
    Parameters
    ----------
    _list : LIST
        Alphanumeric list to be sorted.
    Returns
    -------
    LIST
        Sorted list
    """
    conversion = lambda item: int(item) if item.isdigit() else item
    alphanum_sorting = lambda key: [conversion(n) for n in re.split('([0-9]+)', key)]
    return sorted(_list, key=alphanum_sorting)