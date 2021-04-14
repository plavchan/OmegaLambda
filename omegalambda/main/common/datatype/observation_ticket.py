import datetime
import json
import copy
import re
import logging
from typing import Union, List, Any, Optional, Dict


class ObservationTicket:

    def __init__(self, name: Optional[str] = None, ra: Optional[Union[str, float, int]] = None,
                 dec: Optional[Union[str, float, int]] = None, start_time: Optional[str] = None,
                 end_time: Optional[str] = None, _filter: Optional[Union[str, List[str]]] = None,
                 num: Optional[int] = None, exp_time: Optional[Union[float, int, List[Union[float, int]]]] = None,
                 self_guide: Optional[bool] = None, guide: Optional[bool] = None, cycle_filter: Optional[bool] = None):
        """

        Parameters
        ----------
        name : STR, optional
            Name of intended target, ex: TOI1234.01 . The default is None.
        ra : FLOAT, STR, optional
            Right ascension of target object. The default is None.
        dec : FLOAT, STR, optional
            Declination of target object. The default is None.
        start_time : STR, optional
            Start time of first exposure. The default is None.
        end_time : STR, optional
            End time of last exposure. The default is None.
        _filter : STR or LIST, optional
            List of filters that will be used during observing session.
            The default is None.
        num : INT, optional
            Number of exposures. The default is None.
        exp_time : FLOAT or LIST, optional
            Exposure time of each image in seconds.  List order must match the order of filters.  The default is None.
        self_guide : BOOL, optional
           If True, self-guiding module will activate, keeping the telescope
           pointed steady at the same target with minor adjustments. The default is None.
        guide : BOOl, optional
            If True, activates external guiding module, keeping telescope pointed at the
            same target with minor adjustments. The default is None.
        cycle_filter : BOOL, optional
            If true, filter will cycle after each exposure, if False filter will
            cycle after number specified in num parameter. The default is None.

        Returns
        -------
        None.
        """
        self.name: Optional[str] = name
        if type(ra) is float:
            self.ra: float = ra
            self.dec: float = dec
        elif type(ra) is str:
            parse = True
            splitter = ':' if ':' in ra else 'h|m|s|d' if 'h' in ra else ' ' if ' ' in ra else None
            if not splitter:
                self.ra: float = float(ra)
                self.dec: float = float(dec)
                parse = False
            coords = {'ra': ra, 'dec': dec}
            if parse:
                for key in coords:
                    coord_split = re.split(splitter, coords[key])
                    if float(coord_split[0]) > 0 or coord_split[0] == '+00' or coord_split[0] == '00':
                        coords[key] = float(coord_split[0]) + float(coord_split[1])/60 + float(coord_split[2])/3600
                    elif float(coord_split[0]) < 0 or coord_split[0] == '-00':
                        coords[key] = float(coord_split[0]) - float(coord_split[1])/60 - float(coord_split[2])/3600
                self.ra: float = coords['ra']
                self.dec: float = coords['dec']
        else:
            self.ra: Any = ra
            self.dec: Any = dec
        if start_time:
            self.start_time: datetime.datetime = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S%z")
        else:
            self.start_time: Any = start_time
        if end_time:
            self.end_time: datetime.datetime = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S%z")
        else:
            self.end_time: Any = end_time
        self.filter: Union[str, List[str]] = _filter
        self.num: int = num
        self.exp_time: Union[float, int, List[Union[float, int]]] = exp_time
        self.self_guide: bool = self_guide
        self.guide: bool = guide
        self.cycle_filter: bool = cycle_filter

        if not self.check_ticket():
            raise AttributeError

    @staticmethod
    def deserialized(text: str):
        """
        Parameters
        ----------
        text : JSON STRING
            Takes .json string from json_reader.py to be converted.

        Returns
        -------
        ObservationTicket
            Global observationticket class object to be used by any other process that needs it.
        """
        return json.loads(text, object_hook=_dict_to_obs_object)

    def serialized(self) -> Dict:
        """
        Returns
        -------
        DICT
            Creates copy_obj in dictionary format.
        """
        copy_obj = copy.deepcopy(self)
        if copy_obj.start_time:
            copy_obj.start_time = copy_obj.start_time.isoformat()
        if copy_obj.end_time:
            copy_obj.end_time = copy_obj.end_time.isoformat()
        return copy_obj.__dict__

    def check_ticket(self) -> bool:
        """
        Description
        -----------
        Sanity check for the finalized observation ticket.  Makes sure everything is the right type and
        within the right bounds.

        Returns
        -------
        BOOL
            True if the ticket looks good, False otherwise.

        """
        check = True
        if self.ra < 0 or self.ra > 24:
            logging.error('Error reading ticket: ra not between 0 and 24 hrs')
            check = False
        if abs(self.dec) > 90:
            logging.error('Error reading ticket: dec greater than +90 or less than -90...')
            check = False
        if type(self.start_time) is not datetime.datetime:
            logging.error('Error reading ticket: start time formatting error...')
            check = False
        if type(self.end_time) is not datetime.datetime:
            logging.error('Error reading ticket: end time formatting error...')
            check = False
        if self.num <= 0:
            logging.error('Error reading ticket: num must be > 0.')
            check = False
        if self.exp_time:
            e_times = [self.exp_time] if type(self.exp_time) in (int, float) else self.exp_time
            filts = [self.filter] if type(self.filter) is str else self.filter
            for num in e_times:
                if num < 0.001:
                    logging.error('Error reading ticket: exp_time must be >= 0.001')
                    check = False
            if len(e_times) > 1 and (len(e_times) != len(filts)):
                logging.error('Number of filters and number of exposure times must match!')
                check = False
        return check


def _dict_to_obs_object(dic: Dict) -> ObservationTicket:
    """
    Parameters
    ----------
    dic : DICT
        .json file with proper observation ticket info,
        see ~/test/test.json for proper formatting.

    Returns
    -------
    ObservationTicket OBJECT
        An ObservationTicket object created from the .json file dictionary.
    """
    return ObservationTicket(name=dic['name'], ra=dic['ra'], dec=dic['dec'], start_time=dic['start_time'],
                             end_time=dic['end_time'], _filter=dic['filter'], num=dic['num'], exp_time=dic['exp_time'],
                             self_guide=dic['self_guide'], guide=dic['guide'], cycle_filter=dic['cycle_filter'])