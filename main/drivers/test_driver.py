from main.common.cAmera import *
from main.common.logger import *

#activates the camera function
camera_object = Camera("camera_work")
camera_object.expose(10, 1, type="dark")

#activates the logger function
main('camera_work')
#NEEDS TESTING
