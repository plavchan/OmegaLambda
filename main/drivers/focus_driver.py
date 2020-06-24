from ..controller.focuser import Focuser
from ..controller.camera import Camera
from ..common.IO.json_reader import Reader
from ..common.datatype.object_reader import ObjectReader
from ...logger.logger import Logger

log = Logger(r'C:/Users/GMU Observtory1/-omegalambda/config/logging.json')

global_config = ObjectReader(Reader(r'C:/Users/GMU Observtory1/-omegalambda/config/parameters_config.json'))

cam_obj = Camera()
focus_obj = Focuser(cam_obj, r'H:/Observatory Files/Observing Sessions/2020_Data/20200624')

focus_obj.start()
cam_obj.start()
focus_obj.onThread(focus_obj.AutoFocusProcedure, 10, 4, 10, 2)
focus_obj.onThread(focus_obj.stop)
focus_obj.join()
cam_obj.onThread(cam_obj.stop)