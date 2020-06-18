import itertools
import json
import logging

_filter = None

def get_filter():
    '''
    
    Raises
    ------
    NameError
        Meant only as a way to retrieve an already initialized global filter object, so if that object has not
        been created yet, we raise a name error.

    Returns
    -------
    _filter : CLASS INSTANCE OBJECT of FilterWheel
        Based off of a dictionary generated from a .json config file.  Global object to be passed anywhere
        it is needed--mainly observation_run.py

    '''
    global _filter
    if _filter is None:
        logging.error('Global filter object was called before being initialized')
        raise NameError('Global filter has not been initialized')
    else:
        logging.debug('Global filter object was called')
        return _filter

class FilterWheel():

    def __init__(self, position_1, position_2, position_3, position_4, position_5, position_6, position_7, position_8):
        '''

        Parameters
        ----------
        position_1 - position_8 : STR
            Each position will be the name/label of the filter in said position (i.e. "r" for red filter).
            For readability, each position is labeled by a STR "position_X" rather than just an INT X.

        Returns
        -------
        None.

        '''
        self.position_1 = position_1
        self.position_2 = position_2
        self.position_3 = position_3
        self.position_4 = position_4
        self.position_5 = position_5
        self.position_6 = position_6
        self.position_7 = position_7
        self.position_8 = position_8

    def filter_position_dict(self):
        '''

        Returns
        -------
        DICT
            Reverses the keys and values in our filterwheel dictionary, and transforms the position labels to INTs
            so that it can be properly read by the internal MaxIm DL language.  We need to be able to pass in the
            filter STR that we want (i.e. "r") and have it return the INT for that filter's position, instead of
            the other way around.

        '''
        i = itertools.count(0)
        return {filter:next(i) for filter in self.__dict__.values()}
    
    def serialized(self):
        '''

        Returns
        -------
        DICT
            A way to use the filter_wheel class object as a traditional dictionary, rather than the self-properties
            defined in __init__.

        '''
        return self.__dict__
    
    @staticmethod
    def deserialized(text):
        '''

        Parameters
        ----------
        text : STR
            Pass in a json-formatted STR received from our json_reader and object_readers that is to be decoded into
            a python dictionary. Then, using the object_hook, that dictionary is transformed into our Filterwheel class
            object.

        Returns
        -------
        CLASS INSTANCE OBJECT of FilterWheel
            Global filterwheel class object to be used by any other process that needs it.  Once it has been created,
            it can be called repeatedly thereafter using get_filter.

        '''
        return json.loads(text, object_hook=_dict_to_filter_object)

def _dict_to_filter_object(dict):
    '''

    Parameters
    ----------
    dict : DICT
        A dictionary of our filterwheel config file, generated using json.loads from deserialized.

    Returns
    -------
    _filter : CLASS INSTANCE OBJECT of FilterWheel
        Global filterwheel class object that is also returned by deserialized.

    '''
    global _filter
    _filter = FilterWheel(dict['position_1'], dict['position_2'], dict['position_3'], dict['position_4'],
                          dict['position_5'], dict['position_6'], dict['position_7'], dict['position_8'])
    logging.info('Global filter object has been created')
    return _filter
