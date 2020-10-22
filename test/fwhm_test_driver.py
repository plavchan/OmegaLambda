# MaxIm DL vs. IRAFStarFinder test driver
from ..main.common.util import filereader_utils
from ..main.controller.camera import Camera
from ..main.common.IO.json_reader import Reader
from ..main.common.datatype.object_reader import ObjectReader
from ..main.common.IO import config_reader
from ..logger.logger import Logger

import os
import time
import datetime
import statistics
import matplotlib.pyplot as plt
import astropy.io.fits as fits
import photutils
import numpy as np

# log = Logger(r'C:/Users/GMU Observtory1/-omegalambda/config/logging.json')

global_config = ObjectReader(Reader(r'C:/Users/GMU Observtory1/-omegalambda/config/parameters_config.json'))

# c = Camera()
# c.start()
# c.onThread(c.expose, 10, 4, r'H:/Observatory Files/Observing Sessions/2020_Data/20200629/testimage.fits', 'light')
# c.image_done.wait()
# time.sleep(1)
# c.onThread(c.get_FWHM)
# time.sleep(1)
# MaxImDLfwhm = c.fwhm
# IRAFfwhm = filereader_utils.get_FWHM_from_image(r'H:/Observatory Files/Observing Sessions/2020_Data/20200629/testimage.fits')

# c.onThread(c.disconnect)
# c.onThread(c.stop)

# print("MaxIm DL = {}; IRAFStarFinder = {}.".format(MaxImDLfwhm, IRAFfwhm))
# print("Compare with AIJ Seeing Profile?")
start_time = datetime.datetime.now()
stars, peaks, data, stdev = filereader_utils.findstars(r'H:\Observatory Files\Observing Sessions\2020_Data\20200708\TOI_1403.01_45s_r-0029.fits', 20000, subframe=(3012, 2157), return_data=True)
stars2, peaks2 = filereader_utils.findstars(r'H:\Observatory Files\Observing Sessions\2020_Data\20200708\TOI_1403.01_45s_r-0029.fits', 20000)
# data = fits.getdata(r'H:/Observatory Files/Observing Sessions/2020_Data/20200612/TOI1868.01_120s_r-0001.fits')
end_time = datetime.datetime.now()
print('Total seconds = {}'.format((end_time - start_time).total_seconds()))

print(stars)
print(peaks)

print(stars2)
print(peaks2)
"""
print('Number of stars = {}'.format(len(stars)))
# # data_subframe = np.log(data_subframe)
# apertures = photutils.CircularAperture(stars, r = 6)
# # plt.plot(stars[:][0], stars[:][1], 'ro')
# plt.imshow(data, cmap = 'YlGn')
# apertures.plot(color = 'blue', lw = 1.5, alpha = .5)
# plt.savefig(r'C:/Users/GMU Observtory1/-omegalambda/test/plot.png')

test = filereader_utils.radial_average(r'H:\Observatory Files\Observing Sessions\2020_Data\20200708\TOI_1403.01_45s_r-0029.fits', 20000)
print(test)
test2 = filereader_utils.radial_average(r'H:\Observatory Files\Observing Sessions\2020_Data\20200708\TOI_1403.01_45s_r-0029.fits', 20000)
print(test2)
"""