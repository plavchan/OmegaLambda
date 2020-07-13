#Logging module
import logging
import logging.config
import logging.handlers

from ..main.common.IO.json_reader import Reader
from ..main.common.datatype.object_reader import ObjectReader

class Logger():
    
    def __init__(self, config):
        '''
        Description
        -----------
        Creates logging console and file configurations based on config json file

        Returns
        -------
        None.

        '''
        self.logger_config = ObjectReader(Reader(config))
        logging.config.dictConfig(self.logger_config.ticket)
        
        self.start()
        
    def start(self):
        '''
        Description
        -----------
        Starts the logger module.
        
        Returns
        -------
        None.

        '''
        logging.info('Initialized logging module')
        
    @staticmethod
    def stop():
        '''
        Description
        -----------
        Stops the logger module.

        Returns
        -------
        None.

        '''
        logging.shutdown()
        