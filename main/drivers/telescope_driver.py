from main.controller.telescope import Telescope
from main.controller.dome import Dome
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader

global_config_object = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))

tel_obj = Telescope()
dome_obj = Dome()

tel_obj.Unpark()
tel_obj.Slew(22 + 5/(60*15) + 13.79/(3600*15), 66 + 46/60 + 30.9/3600)
dome_obj.MoveShutter('open')
dome_obj.SlaveDometoScope(True)

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