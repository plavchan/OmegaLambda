'''
JSON-to-string file reader.
Input is a .json file, output is a python string that
is passes on to the deserializer in observation_ticket or filter_wheel.
'''
import json
from main.common.datatype.observation_ticket import ObservationTicket
from main.common.datatype.filter_wheel import FilterWheel

class Reader():
    
    def __init__(self, path=None):
        self.path = path
        
        with open(self.path, 'r') as file:
            self.__dict__ = json.load(file)
        
        self.str = json.dumps(self.__dict__)
        
        self._pass_to_deserializer()
    
    def _pass_to_deserializer(self):
        if list(self.__dict__.keys())[0] == 'name':
            self.ticket = ObservationTicket.deserialized(self.str)
            
        elif list(self.__dict__.keys())[0] == 'position_1':
            self.ticket = FilterWheel.deserialized(self.str)