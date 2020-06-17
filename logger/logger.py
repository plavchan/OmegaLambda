#Logging module
import logging
import logging.config
import logging.handlers
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader

class Logger():
    
    def __init__(self):
        self.logger_config = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\logging.json'))
        logging.config.dictConfig(self.logger_config.ticket)
        self.start()
        
    def start(self):
        logging.info('Started logging module')
        