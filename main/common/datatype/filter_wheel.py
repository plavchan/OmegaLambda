import itertools
import json
import logging
from typing import Dict, Optional


_filter = None


class FilterWheel:

    def __init__(self, position_1: str, position_2: str, position_3: str, position_4: str, position_5: str,
                 position_6: str, position_7: str, position_8: str):
        """

        Parameters
        ----------
        position_1 - position_8 : STR
            Each position will be the name/label of the filter in said position (i.e. "r" for red filter).
            For readability, each position is labeled by a STR "position_X" rather than just an INT X.

        Returns
        -------
        None.

        """
        self.position_1: str = position_1
        self.position_2: str = position_2
        self.position_3: str = position_3
        self.position_4: str = position_4
        self.position_5: str = position_5
        self.position_6: str = position_6
        self.position_7: str = position_7
        self.position_8: str = position_8

    def filter_position_dict(self) -> Dict:
        """

        Returns
        -------
        DICT
            Reverses the keys and values in our filter wheel dictionary, and transforms the position labels to INTs
            so that it can be properly read by the internal MaxIm DL language.  We need to be able to pass in the
            filter STR that we want (i.e. "r") and have it return the INT for that filter's position, instead of
            the other way around.

        """
        i = itertools.count(0)
        return {filter_: next(i) for filter_ in self.__dict__.values()}
    
    def serialized(self) -> Dict:
        """

        Returns
        -------
        DICT
            A way to use the filter_wheel class object as a traditional dictionary, rather than the self-properties
            defined in __init__.

        """
        return self.__dict__
    
    @staticmethod
    def deserialized(text: str):
        """

        Parameters
        ----------
        text : STR
            Pass in a json-formatted STR received from our json_reader and object_readers that is to be decoded into
            a python dictionary. Then, using the object_hook, that dictionary is transformed into our Filter wheel class
            object.

        Returns
        -------
        FilterWheel
            Global filterwheel class object to be used by any other process that needs it.  Once it has been created,
            it can be called repeatedly thereafter using get_filter.

        """
        return json.loads(text, object_hook=_dict_to_filter_object)


def _dict_to_filter_object(dic: Dict) -> FilterWheel:
    """

    Parameters
    ----------
    dic : DICT
        A dictionary of our filter wheel config file, generated using json.loads from deserialized.

    Returns
    -------
    _filter : CLASS INSTANCE OBJECT of FilterWheel
        Global filter wheel class object that is also returned by deserialized.

    """
    global _filter
    _filter = FilterWheel(dic['position_1'], dic['position_2'], dic['position_3'], dic['position_4'],
                          dic['position_5'], dic['position_6'], dic['position_7'], dic['position_8'])
    logging.info('Global filter object has been created')
    return _filter


def get_filter() -> Optional[FilterWheel]:
    """

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

    """
    global _filter
    if _filter is None:
        logging.error('Global filter object was called before being initialized')
        raise NameError('Global filter has not been initialized')
    else:
        logging.debug('Global filter object was called')
        return _filter
