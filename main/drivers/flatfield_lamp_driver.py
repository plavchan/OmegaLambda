# Flatfield Lamp Test Driver
import time

from ..controller.flatfield_lamp import FlatLamp
from ...logger.logger import Logger
from ..common.IO.json_reader import Reader
from ..common.datatype.object_reader import ObjectReader
from ..common.IO import config_reader

log = Logger(r'C:/Users/GMU Observtory1/-omegalambda/config/logging.json')

global_config = ObjectReader(Reader(r'C:/Users/GMU Observtory1/-omegalambda/config/parameters_config.json'))
config_dict = config_reader.get_config()

fl = FlatLamp()
fl.start()
time.sleep(5)
fl.onThread(fl.turn_on)
time.sleep(5)
fl.onThread(fl.turn_off)
time.sleep(5)
fl.onThread(fl.disconnect)
fl.onThread(fl.stop)