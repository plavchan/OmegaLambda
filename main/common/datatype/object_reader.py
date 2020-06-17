from main.common.datatype.observation_ticket import ObservationTicket
from main.common.datatype.filter_wheel import FilterWheel
from main.common.IO.config_reader import Config
import json

class ObjectReader():
    
    def __init__(self, reader_obj):
        global Objects
        self.str = reader_obj.str
        self.type = reader_obj.type
        
        Objects = {"observation_ticket": ObservationTicket, "filter_wheel": FilterWheel, "config": Config, "logging_config": self}
        
        if self.type in Objects:
            self.ticket = Objects[self.type].deserialized(self.str)
            
    @staticmethod
    def deserialized(text):     #Default: No object hook.  Used for logging config file.
        return json.loads(text)