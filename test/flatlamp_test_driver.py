import time

from ..main.common.IO.json_reader import Reader
from ..main.common.datatype.object_reader import ObjectReader
from ..main.controller.flatfield_lamp import FlatLamp

global_config = ObjectReader(Reader(r'C:/Users/GMU Observtory1/-omegalambda/config/parameters_config.json'))

fl = FlatLamp()
time.sleep(5)
fl.turn_on()
time.sleep(5)
fl.turn_off()
time.sleep(5)
fl.disconnect()
