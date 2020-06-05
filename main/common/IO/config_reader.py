import json

_config = None

def get_config():
    global _config
    if _config is None:
        raise NameError('Global config object has not been initialized')
    else:
        return _config

class Config():
    
    def __init__(self, cooler_setpoint=None, cooler_idle_setpoint=None, maximum_jog=None, site_latitude=None, 
                 site_longitude=None, data_directory=None, config_directory=None, ticket_directory=None, prep_time=None):
        self.cooler_setpoint = cooler_setpoint                      #Setpoint in C when running camera's cooler => Our default is -30 C
        self.cooler_idle_setpoint = cooler_idle_setpoint            #Setpoint in C when not running camera's cooler => Our default is +5 C
        self.maximum_jog = maximum_jog                              #Maximum distance in arcseconds to be used for the telescope's jog function => Our default is 1800"
        self.site_latitude = site_latitude                          #Latitude at the telescope's location => Our default is +38.828 degrees
        self.site_longitude = site_longitude                        #Longitude at the telescope's location => Our default is -77.305 degrees
        self.data_directory = data_directory                        #Where images and other data are saved on the computer => Our default is H:\Observatory Files\Observing Sessions\2020_Data
        self.config_directory = config_directory                    #Where configurations files are stored => Our default is C:\Users\GMU Observtory1\-omegalambda\config
        self.ticket_directory = ticket_directory                    #Where observation ticket files are stored and read from => Our default is C:\Users\GMU Observtory1\-omegalambda\test (temporary)
        self.prep_time = prep_time                                  #Preparation time in minutes needed before an observation run to take darks and flats => Our default is 30 minutes
        
    @staticmethod
    def deserialized(text):
        return json.loads(text, object_hook=_dict_to_config_object)
    
    def serialized(self):
        return self.__dict__
    
def _dict_to_config_object(dict):
    global _config
    _config = Config(cooler_setpoint=dict['cooler_setpoint'], cooler_idle_setpoint=dict['cooler_idle_setpoint'],
                     site_latitude=dict['site_latitude'], site_longitude=dict['site_longitude'],
                     maximum_jog=dict['maximum_jog'], data_directory=dict['data_directory'], config_directory=dict['config_directory'],
                     ticket_directory=dict['ticket_directory'], prep_time=dict['prep_time'])
    return _config