from main.common.datatype.observation_ticket import ObservationTicket
from main.common.datatype.filter_wheel import FilterWheel

Objects = {"observation_ticket": ObservationTicket, "filter_wheel": FilterWheel}

class ObjectReader():
    
    def __init__(self, _str, object_name=None):
        global Objects
        self.object_name = object_name
        self.str = _str
        
        if object_name in Objects:
            self.ticket = Objects[object_name].deserialized(self.str)