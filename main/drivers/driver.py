import os
import datetime
import logging

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
    
    if logger:
        log_object = Logger(logger)
    else:
        path = os.path.abspath(os.path.join(current_path, r'../../config/logging.json'))
        log_object = Logger(path)
    # I believe this is the only spot where we actually want to instantiate a logger object
    # everywhere else we can just add messages
    
    try:
        if config:
            global_config = ObjectReader(Reader(config))
        else:
            global_config = ObjectReader(Reader(
                os.path.abspath(os.path.join(current_path, r'../../config/parameters_config.json'))))
    except Exception:
        logging.critical('Could not read or parse config file')
        return

    try: 
        if _filter:
            global_filter = ObjectReader(Reader(_filter))
        else:
            global_filter = ObjectReader(Reader(
                os.path.abspath(os.path.join(current_path, r'../../config/fw_config.json'))))
    except Exception:
        logging.critical('Error initializing global filter object')
        return
    
    config_dict = config_reader.get_config()
    if data:
        folder = r'{}'.format(data)     # Reads as a raw string
    else:
        folder = os.path.join(config_dict.data_directory, datetime.datetime.now().strftime('%Y%m%d'))
    if not os.path.exists(folder):
        os.makedirs(folder)
        print('New directory for tonight\'s observing has been made!')
    else:
        print('Directory for tonight\'s observing already exists!')

    if os.path.isfile(obs_tickets[0]):
        observation_request_list = [ticket_object for ticket in obs_tickets
                                    if (ticket_object := read_ticket(ticket))]
    else:
        observation_request_list = [ticket_object for filename in os.listdir(obs_tickets[0])
                                    if (ticket_object := read_ticket(os.path.join(obs_tickets[0], filename)))]
    
    observation_request_list.sort(key=start_time)
        
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
    except:
        logging.critical('Error reading observation ticket')
        return
    else:
        print('Observation ticket has been read')
    
    if check_ticket(object_reader.ticket):
        return object_reader.ticket
    else:
        logging.critical('Observation ticket formatting error')
        return None


def check_ticket(ticket):
    """
    Description
    -----------
    Sanity check for the finalized observation ticket.  Makes sure everything is the right type and
    within the right bounds.

    Parameters
    ----------
    ticket : CLASS INSTANCE OBJECT of ObservationTicket
        Retrieved from the object_reader.

    Returns
    -------
    BOOL
        True if the ticket looks good, False otherwise.

    """
    check = True
    if type(ticket.name) is not str:
        print('Error reading ticket: name not a string...')
        check = False
    if type(ticket.ra) is not float:
        print('Error reading ticket: ra formatting error...')
        check = False
    if ticket.ra < 0 or ticket.ra > 24:
        print('Error reading ticket: ra not between 0 and 24 hrs')
        check = False
    if type(ticket.dec) is not float:
        print('Error reading ticket: dec formatting error...')
        check = False
    if abs(ticket.dec) > 90:
        print('Error reading ticket: dec greater than +90 or less than -90...')
        check = False
    if type(ticket.start_time) is not datetime.datetime:
        print('Error reading ticket: start time formatting error...')
        check = False
    if type(ticket.end_time) is not datetime.datetime:
        print('Error reading ticket: end time formatting error...')
        check = False
    if type(ticket.filter) not in (str, list):
        print('Error reading ticket: filter not a string or list...')
        check = False
    if type(ticket.num) is not int:
        print('Error reading ticket: num not an integer...')
        check = False
    if ticket.num <= 0:
        print('Error reading ticket: num must be > 0.')
        check = False
    if type(ticket.exp_time) not in (int, float, list):
        print('Error reading ticket: exp_time not an integer, float, or list...')
        check = False
    if ticket.exp_time:
        e_times = [ticket.exp_time] if type(ticket.exp_time) in (int, float) else ticket.exp_time
        filts = [ticket.filter] if type(ticket.filter) is str else ticket.filter
        for num in e_times:
            if num <= 0:
                print('Error reading ticket: exp_time must be > 0.')
                check = False
        if len(e_times) > 1 and (len(e_times) != len(filts)):
            print('Error: number of filters and number of exposure times must match!')
            check = False
    if type(ticket.self_guide) is not bool:
        print('Error reading ticket: self_guide not a boolean...')
        check = False
    if type(ticket.guide) is not bool:
        print('Error reading ticket: guide not a boolean...')
        check = False
    if type(ticket.cycle_filter) is not bool:
        print('Error reading ticket: cycle_filter not a boolean...')
        check = False
    return check


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
