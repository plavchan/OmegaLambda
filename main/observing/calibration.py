# Darks & Flats automation
import os
import threading

from ..common.util import filereader_utils
from ..common.datatype import filter_wheel
from ..controller.hardware import Hardware

class Calibration(Hardware):
    
    def __init__(self, camera_obj, flatlamp_obj, image_directory):
        self.camera = camera_obj
        self.flatlamp = flatlamp_obj
        self.image_directory = image_directory
        self.filterwheel_dict = filter_wheel.get_filter().filter_position_dict()
        self.filter_exp_times = {'clr': 5, 'uv': 240, 'b': 120, 'v': 16, 'r': 8, 'ir': 10, 'Ha': 120}
        
        self.calibration_done = threading.Event()
        super(Calibration, self).__init__(name='Calibration')
        
    def take_flats(self, ticket):
        self.calibration_done.clear()
        self.flatlamp.onThread(self.flatlamp.TurnOn)
        lamp = self.flatlamp.lamp_done.wait(timeout = 60)
        if not lamp:
            return False
        filt = ticket.filter
        if type(filt) is str:
            filters = [filt]
        elif type(filt) is list:
            filters = filt
        
        for f in filters:
            j = 0
            while j < 10:
                image_name = 'Flat_{0:d}s_{1:s}-{2:04d}'.format(self.filter_exp_times[f], f, j + 1)
                self.camera.onThread(self.camera.expose, self.filter_exp_times[f], self.filterwheel_dict[f], 
                                     save_path=os.path.join(self.image_directory, r'Flats_{}'.format(ticket.name), image_name), type='light')
                median = filereader_utils.MedianCounts(os.path.join(self.image_directory, r'Flats_{}'.format(ticket.name), image_name))
                if median > 14000 and median < 21000:
                    j += 1
                if f in ('b', 'uv', 'Ha'):
                    if median < 14000:
                        self.filter_exp_times[f] += 2
                    elif median > 21000:
                        self.filter_exp_times[f] -= 2
                else:
                    if median < 14000:
                        self.filter_exp_times[f] += 10
                    elif median > 21000:
                        self.filter_exp_times[f] -= 10
        self.flatlamp.onThread(self.flatlamp.TurnOff)
        lamp = self.flatlamp.lamp_done.wait(timeout = 60)
        if not lamp:
            return False
        self.calibration_done.set()
        return True
        
    def take_darks(self, ticket):
        self.calibration_done.clear()
        filt = ticket.filter
        if type(filt) is str:
            filters = [filt]
        elif type(filt) is list:
            filters = filt
        
        for f in filters:
            for j in range(10):
                image_name = 'Dark_{0:d}s-{1:04d}'.format(self.filter_exp_times[f], j + 1)
                self.camera.onThread(self.camera.expose, self.filter_exp_times[f], self.filterwheel_dict[f],
                                     save_path=os.path.join(self.image_directory, r'Darks_{}'.format(ticket.name), image_name), type='dark')
        for k in range(10):
            image_name = 'Dark_{0:d}s-{1:04d}'.format(ticket.exp_time, j + 1)
            self.camera.onThread(self.camera.expose, ticket.exp_time, self.filterwheel_dict[f],
                                 save_path=os.path.join(self.image_directory, r'Darks_{}'.format(ticket.name), image_name), type='dark')
        self.calibration_done.set()
        return True