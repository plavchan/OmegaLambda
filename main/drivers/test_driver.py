from main.common.cAmera import Camera
from main.common.logger import Logger

#activates the camera function
camera_object = Camera("camera_work")
camera_object.expose(10, 1, type="dark")

#activates the logger function
logger_object=Logger(Camera)
logger_object

#NEEDS TESTING
