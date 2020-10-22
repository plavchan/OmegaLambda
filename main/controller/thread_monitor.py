import datetime
import time
import os
import re
import logging
import subprocess
import threading

from ..common.IO import config_reader
from ..common.datatype import filter_wheel
from ..controller.camera import Camera
from ..controller.telescope import Telescope
from ..controller.dome import Dome
from ..controller.focuser_control import Focuser
from ..controller.flatfield_lamp import FlatLamp
from ..observing.condition_checker import Conditions

class Monitor(threading.Thread):
    def __init__(self):

        self.camera = Camera()
        self.telescope = Telescope()
        self.dome = Dome()
        self.conditions = Conditions()
        self.focuser = Focuser()
        self.flatlamp = FlatLamp()


        self.tlist = []
        #self.threadlist = threading.enumerate()
        for thread in threading.enumerate():
            self.tlist.append(thread.name)
        print('Threadlist:', self.tlist)
        super(Monitor, self).__init__(name='Monitor')

    def monitor_run(self):
        run = True
        logging.info('Beginning thread monitoring')
        v = threading.Thread(target=self.count(), name='counting')
        v.start()

        while run:
            for threadname in self.tlist:
                if threadname.is_alive():
                    logging.error('{} thread is alive'.format(threadname.name))
                    continue
                else:
                    logging.error('{} thread has raised an exception'.format(threadname.name))
                    #self.restart(self.threadname)
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
        elif threadname == self.conditions:
            self.conditions = Conditions()
            self.conditions.start()

    def count(self):
        global run
        x = 0
        while x <=45:
            time.sleep(1)
            x+= 1
        self.run = False




