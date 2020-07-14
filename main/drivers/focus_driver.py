from ..controller.focuser_procedures import FocusProcedures
from ..controller.camera import Camera
from ..common.IO.json_reader import Reader
from ..common.datatype.object_reader import ObjectReader
from ..common.IO import config_reader
from ...logger.logger import Logger

import os

log = Logger(r'C:/Users/GMU Observtory1/-omegalambda/config/logging.json')

global_config = ObjectReader(Reader(r'C:/Users/GMU Observtory1/-omegalambda/config/parameters_config.json'))
config_dict = config_reader.get_config()

cam_obj = Camera()
fp = FocusProcedures(cam_obj)

cam_obj.start()
fp.start()
try: os.mkdir(os.path.join(config_dict.data_directory, r'20200629'))
except: pass

fp.onThread(fp.startup_focus_procedure, int(config_dict.focus_exposure_multiplier * 10), 4,
            config_dict.initial_focus_delta, os.path.join(config_dict.data_directory, r'20200629'),
            config_dict.long_focus_tolerance, config_dict.focus_max_distance)

fp.focused.wait()
fp.onThread(fp.disconnect)
fp.onThread(fp.stop)
cam_obj.onThread(cam_obj.stop)