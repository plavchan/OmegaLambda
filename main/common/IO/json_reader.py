'''
JSON-to-string file reader.
Input is a .json file, output is a python string that
is passes on to the deserializer in observation_ticket or filter_wheel.
'''
import json

class Reader():
    
    def __init__(self, path):
        self.path = path
        
        with open(self.path, 'r') as file:
            self.__dict__ = json.load(file)
        
        self.str = json.dumps(self.__dict__['details'])
        self.type = self.__dict__['type']
