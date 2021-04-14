import json
import logging
from typing import Dict

from .observation_ticket import ObservationTicket
from .filter_wheel import FilterWheel
from ...common.IO.config_reader import Config
from ...common.IO.json_reader import Reader


class ObjectReader:
    
    def __init__(self, reader_obj: Reader):
        """

        Parameters
        ----------
        reader_obj : CLASS INSTANCE OBJECT of json_reader.Reader
            A class object with properties self.str, self.type, self.path, and self.__dict__, read directly from
            a .json file.

        Returns
        -------
        None.

        """
        self.str: str = reader_obj.str
        self.type: str = reader_obj.type
        
        objects = {"observation_ticket": ObservationTicket, "filter_wheel": FilterWheel, "config": Config,
                   "logging_config": self}
        # Dictionary used to call the correct deserialized function for whichever type of .json file we may have.
        # i.e. if we have an observation ticket, it will call ObservationTicket.deserialized
        
        logging.debug('Object reader is reading a json file')
        if self.type in objects:
            self.ticket: Dict = objects[self.type].deserialized(self.str)
            
    @staticmethod
    def deserialized(text: str) -> Dict:
        """
        Description
        -----------
            Meant only to be used by the logger module config file, since it needs to be in dict format only.

        Parameters
        ----------
        text : STR
            A string read from a .json file.

        Returns
        -------
        DICT
            Python dictionary created from said .json file.

        """
        logging.info('Logger config dict has been created')
        return json.loads(text)
