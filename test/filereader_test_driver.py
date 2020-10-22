# FileReader Testing Driver
import logging
import time

from ..main.common.util import filereader_utils
from ..main.controller.camera import Camera
from ..main.common.IO.json_reader import Reader
from ..main.common.datatype.object_reader import ObjectReader
'''
a = r'H:/Observatory Files/Observing Sessions/2020_Data/20200612/TOI1868.01_120s_r-0092.fits'
b = r'H:/Observatory Files/Observing Sessions/2020_Data/20200202/TOI1302-01_25s_R-0001.fit'

logging.basicConfig(level='INFO', format='%(levelname)s: (%(threadName)-10s) Module: %(module)s | Message: %(message)s')

global_config = ObjectReader(Reader(r'C:/Users/GMU Observtory1/-omegalambda/config/parameters_config.json'))

c = Camera()
c.start()
c.onThread(c.expose, 10, 4, save_path=r'C:/Users/GMU Observtory1/-omegalambda/test/testimage.fits')
c.image_done.wait()

c.onThread(c.get_FWHM)
print(self.fwhm)

c.onThread(c.disconnect)
c.onThread(c.stop)
'''
a = r'H:/Observatory Files/Observing Sessions/2020_Data/20200612/TOI1868.01_120s_r-0092.fits'
b = r'H:/Observatory Files/Observing Sessions/2020_Data/20200202/TOI1302-01_25s_R-0001.fit'

logging.basicConfig(level='INFO', format='%(levelname)s: (%(threadName)-10s) Module: %(module)s | Message: %(message)s')

fwhm = filereader_utils.get_FWHM_from_image(a)
