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

class Monitor(threading.Thread):
    def __init__(self):

        self.camera = Camera()
        self.telescope = Telescope()
        self.dome = Dome()
        self.conditions = Conditions()
        self.focuser = Focuser()
        self.flatlamp = FlatLamp()

        # Initializes higher level structures - focuser, guider, and calibration
        self.focus_procedures = FocusProcedures(self.focuser, self.camera)
        self.calibration = Calibration(self.camera, self.flatlamp, self.image_directories)
        self.guider = Guider(self.camera, self.telescope)

        # Initializes config objects
        self.filterwheel_dict = filter_wheel.get_filter().filter_position_dict()
        self.config_dict = config_reader.get_config()

        self.tlist = [self.camera, self.telescope, self.dome, self.focuser,
                      self.flatlamp, self.guider, self.conditions]
        #self.threadlist = threading.enumerate()
        #for thread in threading.enumerate():
            #self.tlist.append(thread.name)
        super(Monitor, self),__init__(name='Monitor')

    def monitor_run(self):
        run = True
        logging.info('Beginning thread monitoring')
        while run:
            for self.threadname in tlist:
                if self.threadname.is_alive():
                    logging.debug('{0:s} thread is alive'.format(threadname))
                    continue
                else:
                    logging.error('{0:s} thread has raised an exception')
                    self.restart(self.threadname)
            time.sleep(2)

    #def exception_get(self, threadname):

    def restart(self, threadname):
        if threadname == self.camera:
            self.camera = Camera()
            self.camera.start()
        elif threadname == self.telescope:
            self.telescope = Telescope()
            self.telescope.start()
        elif threadname == self.dome:
            self.dome = Dome()
            self.dome.start()
        elif threadname == self.focuser:
            self.focuser = Focuser()
            self.focuser.start()
        elif threadname == self.flatlamp:
            self.flatlamp = FlatLamp()
            self.flatlamp.start()
        elif threadname == self.guider:
            self.guider = Guider()
            self.guider.start()
        elif threadname == self.conditions:
            self.conditions = Conditions()
            self.conditions.start()



