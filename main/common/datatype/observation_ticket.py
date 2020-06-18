import datetime
import json
import copy
import re

class ObservationTicket():

    def __init__(self, name=None, ra=None, dec=None, start_time=None, end_time=None,
                 filter=None, num=None, exp_time=None, self_guide=None, guide=None, cycle_filter=None):
        '''
        

        Parameters
        ----------
        name : STR, optional
            Name of intended target, ex: TOI1234.01 . The default is None.
        ra : FLOAT, STR, optional
            Right ascension of target object. The default is None.
        dec : Float, STR, optional
            Declination of target object. The default is None.
        start_time : TYPE, optional
            Start time of first exposure. The default is None.
        end_time : TYPE, optional
            End time of last exposure. The default is None.
        filter : LIST, optional
            List of filters that will be used during observing sesion. The default is None.
        num : INT, optional
            Number of exposures. The default is None.
        exp_time : TYPE, optional
            Exposure time of each image in seconds. The default is None.
        self_guide : BOOL, optional
           If True, telescope will automatically slew to coordinates specified in ra and dec parameters, if false or empty, will not. The default is None.
        guide : BOOl, optional
            DESCRIPTION. The default is None.
        cycle_filter : BOOL, optional
            If true, filter will cycle after each exposure, if False filter will cycle after number specified in num parameter. The default is None.

        Returns
        -------
        None.

        '''
        self.name = name
        if type(ra) is float:
            self.ra = ra
            self.dec = dec
        elif type(ra) is str:
            if ':' in ra:
                splitter = ':'
            elif 'h' in ra:
                splitter = 'h|m|s|d'
            coords = {'ra': ra, 'dec': dec}
            for key in coords:
                coords_split = re.split(splitter, coords[key])
                if float(coords_split[0]) > 0 or coords_split[0] == '+00' or coords_split[0] == '00':
                    coords[key] = float(coords_split[0]) + float(coords_split[1])/60 + float(coords_split[2])/3600
                elif float(coords_split[0]) < 0 or coords_split[0] == '-00':
                    coords[key] = float(coords_split[0]) - float(coords_split[1])/60 - float(coords_split[2])/3600
            self.ra = coords['ra']
            self.dec = coords['dec']
        if start_time:
            self.start_time = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S%z")
        else:
            self.start_time = start_time
        if end_time:
            self.end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S%z")
        else:
            self.end_time = end_time
        self.filter = filter
        self.num = num
        self.exp_time = exp_time
        self.self_guide = self_guide
        self.guide = guide
        self.cycle_filter = cycle_filter

    @staticmethod
    def deserialized(text):
        '''
        This decodes a JSON string to an ObservationTicket object.

        :param text: JSON STRING
        :return: ObservationTicket
        '''
        return json.loads(text, object_hook=_dict_to_obs_object)

    def serialized(self):
        '''
        

        Returns
        -------
        TYPE
            DESCRIPTION.

        '''
        copy_obj = copy.deepcopy(self)
        if copy_obj.start_time:
            copy_obj.start_time = copy_obj.start_time.isoformat()
        if copy_obj.end_time:
            copy_obj.end_time = copy_obj.end_time.isoformat()
        return copy_obj.__dict__


def _dict_to_obs_object(dict):
    '''
    

    Parameters
    ----------
    dict : TYPE
        DESCRIPTION.

    Returns
    -------
    TYPE
        DESCRIPTION.

    '''
    return ObservationTicket(name=dict['name'], ra=dict['ra'], dec=dict['dec'], start_time=dict['start_time'],
                             end_time=dict['end_time'], filter=dict['filter'], num=dict['num'], exp_time=dict['exp_time'],
                             self_guide=dict['self_guide'], guide=dict['guide'], cycle_filter=dict['cycle_filter'])