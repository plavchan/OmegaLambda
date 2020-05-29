from main.controller.telescope import Telescope
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader
import time

global_config_object = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))

tel_obj = Telescope()

tel_obj.Unpark()
tel_obj.Slew(5 + 56/60 + 14.111/3600, 7 + 24/60 + 30.86/3600)
#tel_obj.SlewAltAz(105, 63)

#tel_obj.Jog("up", 30)
'''
time.sleep(5)
tel_obj.Jog("right", 5*60)
time.sleep(5)
tel_obj.Jog("down", 30*60)
time.sleep(5)
tel_obj.Jog("left", 45*60)
time.sleep(5)
'''
#tel_obj.Park()

#tel_obj.disconnect()


'''
import win32com.client      #needed to load COM objects
x = win32com.client.Dispatch("ASCOM.Utilities.Chooser")

x.DeviceType = 'Telescope'
print(x.Choose(None))
'''

'''
PARK POSITION LOCAL COORDINATES:
    
    AZ = 180d 06' 26" = 180.10722222
    ALT = +54d 59' 37" = 54.99361111
    
'''