import json

_config = None

def get_config():
    global _config
    if _config is None:
        raise NameError('Global config object has not been initialized')
    else:
        return _config

class Config():
    
    def __init__(self, cooler_setpoint=None, cooler_idle_setpoint=None, site_latitude=None, 
                 site_longitude=None, utc_offset=None, maximum_jog=None):
        self.cooler_setpoint = cooler_setpoint
        self.cooler_idle_setpoint = cooler_idle_setpoint
        self.site_latitude = site_latitude
        self.site_longitude = site_longitude
        self.utc_offset = utc_offset
        self.maximum_jog = maximum_jog
        
    @staticmethod
    def deserialized(text):
        return json.loads(text, object_hook=_dict_to_config_object)
    
    def serialized(self):
        return self.__dict__
    
def _dict_to_config_object(dict):
    global _config
    _config = Config(cooler_setpoint=dict['cooler_setpoint'], cooler_idle_setpoint=dict['cooler_idle_setpoint'],
                     site_latitude=dict['site_latitude'], site_longitude=dict['site_longitude'], utc_offset=dict['utc_offset'],
                     maximum_jog=dict['maximum_jog'])
    return _config