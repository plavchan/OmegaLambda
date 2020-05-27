from main.controller.dome import Dome
from main.controller.telescope import Telescope
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader
import time

global_config_object = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))

dome_obj = Dome()
tel_obj = Telescope()

dome_obj.SlaveDometoScope()
tel_obj.Slew(8,60)
tel_obj.Park()
dome_obj.SlaveDometoScope() #True/False
dome_obj.Park()
# while dome_obj.Slewing == True: wait
# while dome_obj.AtPark == False: wait
'''
dome_obj.Home()
time.sleep(5)
dome_obj.SlaveDometoScope()         #Start slaving
time.sleep(5)
dome_obj.SlaveDometoScope()         #Stop slaving
#dome_obj.MoveShutter('open')
dome_obj.Slew(150)
time.sleep(5)
dome_obj.Park()
time.sleep(10)
#dome_obj.MoveShutter()
'''
dome_obj.disconnect()
tel_obj.disconnect()