import json
import logging
from numpy import pi

_config = None


def get_config():
    """

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

    """
    global _config
    if _config is None:
        logging.error('Global config object was called before being initialized')
        raise NameError('Global config object has not been initialized')
    else:
        logging.debug('Global config object was called')
        return _config


class Config:
    
    def __init__(self, cooler_setpoint=None, cooler_idle_setpoint=None, cooler_settle_time=None, maximum_jog=None,
                 site_latitude=None, site_longitude=None, humidity_limit=None, wind_limit=None, weather_freq=None,
                 cloud_cover_limit=None, user_agent=None, cloud_satellite=None,
                 min_reopen_time=None, plate_scale=None, saturation=None, focus_exposure_multiplier=None,
                 initial_focus_delta=None, quick_focus_tolerance=None, focus_max_distance=None, guiding_threshold=None,
                 guider_ra_dampening=None, guider_dec_dampening=None, guider_max_move=None, guider_angle=None,
                 data_directory=None, calibration_time=None, calibration_num=None):
        """

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
            Frequency of weather checks in minutes.  Our default is 10 minutes.
        cloud_cover_limit : FLOAT, optional
            Limit for percentage of sky around Fairfax to be covered by clouds before closing up.  Our default is 75%.
        user_agent : STR, optional
            Internet user agent for connections, specifically to weather.com.  Our default is Mozilla/5.0.
        cloud_satellite : STR, optional
            Which satellite to use to check for cloud cover.  Currently only supports goes-16.  Our default is goes-16.
        min_reopen_time : INT or FLOAT, optional
            Minimum wait time to reopen (in minutes) after a weather check has gone off.  Our default is 30 minutes.
        plate_scale : FLOAT, optional
            CCD camera conversion factor between pixels and arcseconds, in arcseconds/pixel.  Our default is
            0.350 arcseconds/pixel.
        saturation : INT, optional
            CCD camera saturation limit for exposure in counts.  This is more like the exposure linearity limit, after
            which you'd prefer not to have targets pass.  Our default is 25,000 counts.
        focus_exposure_multiplier : FLOAT, optional
            Multiplier for exposure times on focusing images.  The multiplier is applied to the exposure time for the
            current ticket.  Our default is 0.33.
        initial_focus_delta : INT, optional
            Initial number of steps the focuser will move for each adjustment.  Our default is 15 steps.
        quick_focus_tolerance : FLOAT, optional
            Leniency for how far to let the focus drift before correcting over the course of the night, in
            arcseconds. Our default is 1.25 arcseconds.
        focus_max_distance : INT, optional
            Maximum distance away from the initial focus position that the focuser can move.  Our default is 100 steps.
        guiding_threshold : FLOAT, optional
            How far to let a star drift, in arcseconds, before making a guiding correction. Our default is 10
            arcseconds.
        guider_ra_dampening : FLOAT, optional
            Dampening coefficient for guider telescope corrections on the RA axis.  Our default is 0.75.
        guider_dec_dampening : FLOAT, optional
            Dampening coefficient for guider telescope corrections on the Dec axis.  Our default is 0.5.
        guider_max_move : FLOAT, optional
            The maximum distance in arcseconds that the guider can make adjustments for.  Our default is 30 arcseconds.
        guider_angle : FLOAT, optional
            The clocking angle of the CCD camera's x and y axes against the RA and Dec axes of the telescope, in
            degrees.  Our default is 0.0 degrees.
        data_directory : STR, optional
            Where images and other data are saved on the computer.  Our default is
            H:/Observatory Files/Observing Sessions/2020_Data.
        calibration_time : STR, optional
            If darks and flats should be taken at the start or end of a given observing session.  Can be str "start"
            or "end."  If "start", it will take darks and flats for ALL observing tickets at the start of the night.
            If "end", it will take darks and flats for all FINISHED tickets at the end of the night.
            Our default is "end".
        calibration_num : INT, optional
            The number of darks and flats that should be taken per target.  Note that there will be one set of flats
            with this number of exposures, but two sets of darks, each with this number of exposures: one to match
            the flat exposure time and the other to match the science exposure time.  Our default is 10.

        Returns
        -------
        None.

        """
        self.cooler_setpoint = cooler_setpoint                      
        self.cooler_idle_setpoint = cooler_idle_setpoint            
        self.cooler_settle_time = cooler_settle_time                
        self.maximum_jog = maximum_jog                             
        self.site_latitude = site_latitude                    
        self.site_longitude = site_longitude                
        self.humidity_limit = humidity_limit                      
        self.wind_limit = wind_limit                         
        self.weather_freq = weather_freq 
        self.cloud_cover_limit = cloud_cover_limit
        self.user_agent = user_agent
        self.cloud_satellite = cloud_satellite
        self.min_reopen_time = min_reopen_time
        self.plate_scale = plate_scale
        self.saturation = saturation
        self.focus_exposure_multiplier = focus_exposure_multiplier
        self.initial_focus_delta = initial_focus_delta
        self.quick_focus_tolerance = quick_focus_tolerance/self.plate_scale
        # These two are converted back into pixels for use in the focuser module
        self.focus_max_distance = focus_max_distance
        self.guiding_threshold = int(guiding_threshold/self.plate_scale)        # Input in arcsec, output in pixels
        self.guider_ra_dampening = guider_ra_dampening
        self.guider_dec_dampening = guider_dec_dampening
        self.guider_max_move = guider_max_move                                  # Input in arcsec, output in arcsec
        self.guider_angle = guider_angle*pi/180
        self.data_directory = data_directory                     
        self.calibration_time = calibration_time
        self.calibration_num = int(calibration_num)
        
    @staticmethod
    def deserialized(text):
        """

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

        """
        return json.loads(text, object_hook=_dict_to_config_object)
    
    def serialized(self):
        """

        Returns
        -------
        DICT
            A way to use the config class object as a traditional dictionary, rather than the self-properties
            defined in __init__.

        """
        return self.__dict__


def _dict_to_config_object(dic):
    """

    Parameters
    ----------
    dic : DICT
        A dictionary of our config file, generated using json.loads from deserialized.

    Returns
    -------
    _config : CLASS INSTANCE OBJECT of Config
        Global config class object that is also returned by deserialized.

    """
    global _config
    _config = Config(cooler_setpoint=dic['cooler_setpoint'], cooler_idle_setpoint=dic['cooler_idle_setpoint'],
                     cooler_settle_time=dic['cooler_settle_time'], site_latitude=dic['site_latitude'],
                     site_longitude=dic['site_longitude'], maximum_jog=dic['maximum_jog'],
                     humidity_limit=dic['humidity_limit'], wind_limit=dic['wind_limit'],
                     weather_freq=dic['weather_freq'], cloud_cover_limit=dic['cloud_cover_limit'],
                     user_agent=dic['user_agent'], cloud_satellite=dic['cloud_satellite'],
                     min_reopen_time=dic['min_reopen_time'], plate_scale=dic['plate_scale'],
                     saturation=dic['saturation'], focus_exposure_multiplier=dic['focus_exposure_multiplier'],
                     initial_focus_delta=dic['initial_focus_delta'], quick_focus_tolerance=dic['quick_focus_tolerance'],
                     focus_max_distance=dic['focus_max_distance'], guiding_threshold=dic['guiding_threshold'],
                     guider_ra_dampening=dic['guider_ra_dampening'], guider_dec_dampening=dic['guider_dec_dampening'],
                     guider_max_move=dic['guider_max_move'], guider_angle=dic['guider_angle'],
                     data_directory=dic['data_directory'], calibration_time=dic['calibration_time'],
                     calibration_num=dic['calibration_num'])
    logging.info('Global config object has been created')
    return _config
