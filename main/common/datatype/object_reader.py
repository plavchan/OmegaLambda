from main.common.datatype.observation_ticket import ObservationTicket
from main.common.datatype.filter_wheel import FilterWheel
from main.common.IO.config_reader import Config

Objects = {"observation_ticket": ObservationTicket, "filter_wheel": FilterWheel, "config": Config}

class ObjectReader():
    
    def __init__(self, reader_obj):
        global Objects
        self.str = reader_obj.str
        self.type = reader_obj.type
        
        if self.type in Objects:
            self.ticket = Objects[self.type].deserialized(self.str)