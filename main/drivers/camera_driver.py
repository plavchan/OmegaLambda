from ..controller.camera import Camera
from ..common.IO.json_reader import Reader
from ..common.datatype.object_reader import ObjectReader
import threading
import logging

logging.basicConfig(level=logging.DEBUG, format='(%(threadName)-10s) %(message)s',)

global_config_object = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))
camera_object = Camera()

camera_object.start()
for i in range(6):
    camera_object.onThread(camera_object.expose, 2, 4, r'H:\Observatory Files\Observing Sessions\2020_Data\20200605\test-{0:04d}.fits'.format(i + 1), "light")
    camera_object.image_done.wait()
    
camera_object.onThread(camera_object.disconnect)
camera_object.onThread(camera_object.stop)