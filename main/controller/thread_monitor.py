import datetime
import time
import os
import re
import logging
import subprocess
# import threading

from ..common.util import time_utils, conversion_utils
from ..common.IO import config_reader
from ..common.datatype import filter_wheel
from ..controller.camera import Camera
from ..controller.telescope import Telescope
from ..controller.dome import Dome
from ..controller.focuser_control import Focuser
from ..controller.focuser_procedures import FocusProcedures
from ..controller.flatfield_lamp import FlatLamp
from .calibration import Calibration
from .guider import Guider
from .condition_checker import Conditions

class monitor(threading.Thread):
    def __init__(self):

        self.camera = Camera()
        self.telescope = Telescope()
        self.dome = Dome()
        self.focuser = Focuser()
        self.filterwheel = filter_wheel()
        self.guider = Guider()
        self.conditions = Conditions()

        self.tlist = []
        self.threadlist = threading.enumerate()
        for thread in threading.enumerate():
            self.tlist.append(thread.name)

    def monitor_run(self):
        run = True
        logging.info('Beginning thread monitoring')
        while run = True:


