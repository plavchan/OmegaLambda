from main.controller.telescope import Telescope
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader
import logging

logging.basicConfig(level=logging.DEBUG, format='(%(threadName)-10s) %(message)s',)

global_config_object = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))
tel_obj = Telescope()

tel_obj.start()
tel_obj.onThread(tel_obj.Unpark)
tel_obj.Unpark()
tel_obj.onThread(tel_obj.Slew, 8.8, -1.9)
tel_obj.onThread(tel_obj.Park)
tel_obj.onThread(tel_obj.disconnect)
tel_obj.onThread(tel_obj.stop)

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