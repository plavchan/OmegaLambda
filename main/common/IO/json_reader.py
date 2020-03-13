import json

class Reader():
    
    def __init__(self, path=None):
        self.path = path
        
        with open(self.path, 'r') as file:
            self.__dict__ = json.load(file)
        
        self.str = json.dumps(self.__dict__)