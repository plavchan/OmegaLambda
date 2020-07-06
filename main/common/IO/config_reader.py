import json
import logging

_config = None

def get_config():
    '''

    Raises
    ------
    NameError
        Meant only as a way to retrieve an already initialized global config object, so if that object has not
        been created yet, we raise a name error.

    Returns
    -------
    _config : CLASS INSTANCE OBJECT of Config
        Based off of a dictionary generated from a .json config file.  Global object to be passed anywhere
        it is needed.

    '''
    global _config
    if _config is None:
        logging.error('Global config object was called before being initialized')
        raise NameError('Global config object has not been initialized')
    else:
        logging.debug('Global config object was called')
        return _config

class Config():
    
    def __init__(self, cooler_setpoint=None, cooler_idle_setpoint=None, cooler_settle_time=None, maximum_jog=None, site_latitude=None, 
                 site_longitude=None, humidity_limit=None, wind_limit=None, weather_freq=None, min_reopen_time=None, plate_scale=None, saturation=None,
                 focus_exposure_multiplier=None, initial_focus_delta=None, long_focus_tolerance=None, quick_focus_tolerance=None, focus_max_distance=None, 
                 guiding_threshold=None, guider_ra_dampening=None, guider_dec_dampening=None, guider_max_move=None, data_directory=None, home_directory=None, prep_time=None):
        '''

        Parameters
        ----------
        cooler_setpoint : INT, optional
            Setpoint in C when running camera cooler.  Our default is -30 C.
        cooler_idle_setpoint : INT, optional
            Setpoint in C when not running camera cooler.  Our default is +5 C.
        cooler_settle_time : INT, optional
            Time in minutes given for the cooler to settle to its setpoint. Our default is 5-10 minutes.
        maximum_jog : INT, optional
            Maximum distance in arcseconds to be used for the telescope jog function. Our default is 1800 arcseconds.
        site_latitude : FLOAT, optional
            Latitude at the telescope location.  Our default is +38.828 degrees.
        site_longitude : FLOAT, optional
            Longitude at the telescope location.  Our default is -77.305 degrees.
        humidity_limit : INT, optional
            Limit for humidity while observing.  Our default is 85%.
        wind_limit : INT, optional
            Limit for wind speed in mph while observing.  Our default is 20 mph.
        weather_freq : INT, optional
            Frequency of weather checks in minutes.  Our default is 15 minutes.
        min_reopen_time : INT or FLOAT, optional
            Minimum wait time to reopen (in minutes) after a weather check has gone off.  Our default is 30 minutes.
        plate_scale : FLOAT, optional
            CCD camera conversion factor between pixels and arcseconds, in arcseconds/pixel.  Our default is 0.350 arcseconds/pixel.
        saturation : INT, optional
            CCD camera saturation limit for exposure in counts.  Our default is 20,000 counts.
        focus_exposure_multiplier : FLOAT, optional
            Multiplier for exposure times on focusing images.  The multiplier is applied to the exposure time for the current ticket.  Our default is 0.5.
        initial_focus_delta : INT, optional
            Initial number of steps the focuser will move for each adjustment.  Our default is 10 steps.
        long_focus_tolerance : FLOAT, optional
            Leniency for how close to get the focus within the minimum found during initial focusing, in arcseconds.  Our default is 1.0 arcsecond.
        quick_focus_tolerance : FLOAT, optional
            Leniency for how far to let the focus drift before correcting over the course of the night, in arcseconds.  Our default is 2.0 arcseconds.
        focus_max_distance : INT, optional
            Maximum distance away from the initial focus position that the focuser can move.  Our default is 100 steps.
        guiding_threshold : FLOAT, optional
            How far to let a star drift, in arcseconds, before making a guiding correction. Our default is 20 arcseconds.
        guider_ra_dampening : FLOAT, optional
            Dampening coefficient for guider telescope corrections on the RA axis.  Our default is 0.75.
        guider_dec_dampening : FLOAT, optional
            Dampening coefficient for guider telescope corrections on the Dec axis.  Our default is 0.5.
        guider_max_move : FLOAT, optional
            The maximum distance in arcseconds that the guider can make adjustments for.  Our default is 100 arcseconds.
        data_directory : STR, optional
            Where images and other data are saved on the computer.  Our default is H:/Observatory Files/Observing Sessions/2020_Data.
        home_directory : STR, optional
            Where the home of our code base is.  Our default is C:/Users/GMU Observtory1/-omegalambda.
        prep_time : INT, optional
            Preparation time in minutes needed before an observation run to take darks and flats.  Our default is 30 minutes.

        Returns
        -------
        None.

        '''
        self.cooler_setpoint = cooler_setpoint                      
        self.cooler_idle_setpoint = cooler_idle_setpoint            
        self.cooler_settle_time = cooler_settle_time                
        self.maximum_jog = maximum_jog                             
        self.site_latitude = site_latitude                    
        self.site_longitude = site_longitude                
        self.humidity_limit = humidity_limit                      
        self.wind_limit = wind_limit                         
        self.weather_freq = weather_freq 
        self.min_reopen_time = min_reopen_time
        self.plate_scale = plate_scale
        self.saturation = saturation
        self.focus_exposure_multiplier = focus_exposure_multiplier
        self.initial_focus_delta = initial_focus_delta
        self.long_focus_tolerance = long_focus_tolerance/self.plate_scale       # These two are converted back into pixels for use in the focuser module
        self.quick_focus_tolerance = quick_focus_tolerance/self.plate_scale
        self.focus_max_distance = focus_max_distance     
        self.guiding_threshold = int(guiding_threshold/self.plate_scale)
        self.guider_ra_dampening = guider_ra_dampening
        self.guider_dec_dampening = guider_dec_dampening
        self.guider_max_move = guider_max_move
        self.data_directory = data_directory                     
        self.home_directory = home_directory                        
        self.prep_time = prep_time
        
    @staticmethod
    def deserialized(text):
        '''

        Parameters
        ----------
        text : STR
            Pass in a json-formatted STR received from our json_reader and object_readers that is to be decoded into
            a python dictionary. Then, using the object_hook, that dictionary is transformed into our Config class
            object.

        Returns
        -------
        CLASS INSTANCE OBJECT of Config
            Global config class object to be used by any other process that needs it.  Once it has been created,
            it can be called repeatedly thereafter using get_config.

        '''
        return json.loads(text, object_hook=_dict_to_config_object)
    
    def serialized(self):
        '''

        Returns
        -------
        DICT
            A way to use the config class object as a traditional dictionary, rather than the self-properties
            defined in __init__.

        '''
        return self.__dict__
    
def _dict_to_config_object(dict):
    '''

    Parameters
    ----------
    dict : DICT
        A dictionary of our config file, generated using json.loads from deserialized.

    Returns
    -------
    _config : CLASS INSTANCE OBJECT of Config
        Global config class object that is also returned by deserialized.

    '''
    global _config
    _config = Config(cooler_setpoint=dict['cooler_setpoint'], cooler_idle_setpoint=dict['cooler_idle_setpoint'],
                     cooler_settle_time=dict['cooler_settle_time'], site_latitude=dict['site_latitude'], site_longitude=dict['site_longitude'], 
                     maximum_jog=dict['maximum_jog'], humidity_limit=dict['humidity_limit'], wind_limit=dict['wind_limit'], weather_freq=dict['weather_freq'],
                     min_reopen_time=dict['min_reopen_time'], plate_scale=dict['plate_scale'], saturation=dict['saturation'], focus_exposure_multiplier=dict['focus_exposure_multiplier'], 
                     initial_focus_delta=dict['initial_focus_delta'], long_focus_tolerance=dict['long_focus_tolerance'], quick_focus_tolerance=dict['quick_focus_tolerance'],
                     focus_max_distance=dict['focus_max_distance'], guiding_threshold=dict['guiding_threshold'], guider_ra_dampening=dict['guider_ra_dampening'],
                     guider_dec_dampening=dict['guider_dec_dampening'], guider_max_move=dict['guider_max_move'], data_directory=dict['data_directory'], 
                     home_directory=dict['home_directory'], prep_time=dict['prep_time'])
    logging.info('Global config object has been created')
    return _config