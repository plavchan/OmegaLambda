from main.controller.camera import Camera
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader
import threading
import logging

logging.basicConfig(level=logging.DEBUG, format='(%(threadName)-10s) %(message)s',)

global_config_object = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))
camera_object = Camera()

camera_object.start()
camera_object.onThread(camera_object.expose, 2, 4)
camera_object.onThread(camera_object.disconnect)
camera_object.onThread(camera_object.stop)