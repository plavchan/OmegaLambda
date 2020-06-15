from main.observing.weather_checker import Weather
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader
import time
import logging

cfg = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))
logging.basicConfig(level=logging.DEBUG, format='(%(threadName)-10s) %(message)s',)

w = Weather()
w.start()
time.sleep(2)
w.stop()