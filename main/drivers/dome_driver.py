from ..controller.dome import Dome
from ..controller.telescope import Telescope
from ..common.IO.json_reader import Reader
from ..common.datatype.object_reader import ObjectReader
import logging

logging.basicConfig(level=logging.DEBUG, format='(%(threadName)-10s) %(message)s',)

global_config_object = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))
dome_obj = Dome()
tel_obj = Telescope()

dome_obj.start()
dome_obj.onThread(dome_obj.home)
dome_obj.onThread(dome_obj.slave_dome_to_scope, True)
dome_obj.onThread(dome_obj.slave_dome_to_scope, False)
dome_obj.onThread(dome_obj.park)
dome_obj.onThread(dome_obj.disconnect)
dome_obj.onThread(dome_obj.stop)

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