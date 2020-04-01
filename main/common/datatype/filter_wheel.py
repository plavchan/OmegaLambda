import itertools
import json

_filter = None

def get_filter():
    global _filter
    if _filter is None:
        raise NameError('Global filter has not been initialized')
    else:
        return _filter

class FilterWheel():

    def __init__(self, position_1, position_2, position_3, position_4, position_5, position_6, position_7, position_8):
        self.position_1 = position_1
        self.position_2 = position_2
        self.position_3 = position_3
        self.position_4 = position_4
        self.position_5 = position_5
        self.position_6 = position_6
        self.position_7 = position_7
        self.position_8 = position_8

    def filter_position_dict(self):
        i = itertools.count(0)
        return {filter:next(i) for filter in self.__dict__.values()}
    
    def serialized(self):
        return self.__dict__
    
    @staticmethod
    def deserialized(text):
        return json.loads(text, object_hook=_dict_to_filter_object)

def _dict_to_filter_object(dict):
    global _filter
    _filter = FilterWheel(dict['position_1'], dict['position_2'], dict['position_3'], dict['position_4'],
                       dict['position_5'], dict['position_6'], dict['position_7'], dict['position_8'])
    return _filter
