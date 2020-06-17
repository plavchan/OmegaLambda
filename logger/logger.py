#Logging module
import logging
import logging.config
import logging.handlers
import os
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader
from main.common.IO import config_reader

class Logger():
    
    def __init__(self):
        self.config_dict = config_reader.get_config()
        path = os.path.join(self.config_dict.home_directory, r'config\logging.json')
        self.logger_config = ObjectReader(Reader(path))
        logging.config.dictConfig(self.logger_config.ticket)
        self.start()
        
    def start(self):
        logging.info('Started logging module')
        