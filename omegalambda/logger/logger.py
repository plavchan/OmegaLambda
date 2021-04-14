# Logging module
import os
import logging
import logging.config
import logging.handlers

from ..main.common.IO.json_reader import Reader
from ..main.common.datatype.object_reader import ObjectReader


class Logger:

    def __init__(self, config):
        """
        Description
        -----------
        Creates logging console and file configurations based on config json file

        Returns
        -------
        None.

        """
        self.logger_config = ObjectReader(Reader(config))
        current_path = os.path.abspath(os.path.dirname(__file__))
        self.logger_config.ticket['handlers']['file']['filename'] = os.path.abspath(os.path.join(
            current_path, r'omegalambda_log.log'))
        logging.config.dictConfig(self.logger_config.ticket)

        logging.info('Initialized logging module')

    @staticmethod
    def stop():
        """
        Description
        -----------
        Stops the logger module.

        Returns
        -------
        None.

        """
        logging.shutdown()
