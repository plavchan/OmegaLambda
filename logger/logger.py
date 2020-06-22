#Logging module
import logging
import logging.config
import logging.handlers
import os

from ..main.common.IO.json_reader import Reader
from ..main.common.datatype.object_reader import ObjectReader

class Logger():
    
    def __init__(self):
        '''
        Description
        -----------
        Creates logging console and file configurations based on config json file

        Returns
        -------
        None.

        '''
        current_path = os.path.abspath(os.path.dirname(__file__))
        
        path = os.path.join(current_path, r'../config/logging.json')
        self.logger_config = ObjectReader(Reader(path))
        logging.config.dictConfig(self.logger_config.ticket)
        
        self.start()
        
    def start(self):
        '''

        Returns
        -------
        None.

        '''
        logging.info('Initialized logging module')
        