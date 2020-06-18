'''
JSON-to-string file reader.
Input is a .json file, output is a python string that
is passed on to the deserializer in observation_ticket, filter_wheel, or config_reader.
'''
import json

class Reader():
    
    def __init__(self, path):
        '''
        
        Parameters
        ----------
        path : STR
            Path to desired json file to be converted into a string.

        Returns
        -------
        None.

        '''
        self.path = path
        
        with open(self.path, 'r') as file:
            self.__dict__ = json.load(file)
        
        self.str = json.dumps(self.__dict__['details'])
        self.type = self.__dict__['type']
