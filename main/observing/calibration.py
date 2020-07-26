# Darks & Flats automation
import os
import threading
import logging

from ..common.IO import config_reader
from ..common.util import filereader_utils
from ..common.datatype import filter_wheel
from ..controller.hardware import Hardware


class Calibration(Hardware):
    
    def __init__(self, camera_obj, flatlamp_obj, image_directory):
        """
        Initializes the calibration module as a subclass of hardware.

        Parameters
        ----------
        camera_obj : Camera Object
            Initialized camera.
        flatlamp_obj : FlatLamp Object
            Initialized flat lamp.
        image_directory : STR
            Path to where image files are saved.

        Returns
        -------
        None.

        """
        self.camera = camera_obj
        self.flatlamp = flatlamp_obj
        self.image_directory = image_directory
        self.filterwheel_dict = filter_wheel.get_filter().filter_position_dict()
        self.filter_exp_times = {'clr': 5, 'uv': 240, 'b': 120, 'v': 16, 'r': 8, 'ir': 10, 'Ha': 120}
        self.config_dict = config_reader.get_config()
        
        self.flats_done = threading.Event()
        self.darks_done = threading.Event()
        super(Calibration, self).__init__(name='Calibration')
        
    def take_flats(self, ticket):
        """
        Description
        -----------
        Takes flatfield images for a target.

        Parameters
        ----------
        ticket : ObservationTicket Object
            Created using json_reader and object_reader.

        Returns
        -------
        bool
            True if successful, otherwise False.

        """
        self.flats_done.clear()
        self.flatlamp.onThread(self.flatlamp.turn_on)
        lamp = self.flatlamp.lamp_done.wait(timeout=60)
        if not lamp:
            return False
        filt = ticket.filter
        if type(filt) is str:
            filters = [filt]
        elif type(filt) is list:
            filters = filt
        else:
            logging.error('Filter argument is wrong type')
            return
        try:
            os.mkdir(os.path.join(self.image_directory, 'Flats_{}'.format(ticket.name)))
        except:
            logging.warning('Could not create flat folder, or folder already exists...')
        for f in filters:
            j = 0
            while j < 10:
                image_name = 'Flat_{0:d}s_{1:s}-{2:04d}.fits'.format(self.filter_exp_times[f], f, j + 1)
                self.camera.onThread(self.camera.expose, self.filter_exp_times[f], self.filterwheel_dict[f], 
                                     save_path=os.path.join(self.image_directory, r'Flats_{}'.format(ticket.name),
                                                            image_name), type='light')
                self.camera.image_done.wait()
                median = filereader_utils.mediancounts(os.path.join(
                    self.image_directory, r'Flats_{}'.format(ticket.name), image_name))
                if j == 0 and median < self.config_dict.saturation:
                    # Calculate exposure time
                    desired = 15000
                    scale_factor = desired/median
                    self.filter_exp_times[f] = int(self.filter_exp_times[f]*scale_factor)
                    if self.filter_exp_times[f] <= 1:
                        self.filter_exp_times[f] = 1
                    j += 1
                elif j == 0 and median >= self.config_dict.saturation:
                    self.filter_exp_times[f] = self.filter_exp_times[f]//2
                    if self.filter_exp_times[f] <= 1:
                        self.filter_exp_times[f] = 1
                else:
                    j += 1
                    continue
        self.flatlamp.onThread(self.flatlamp.turn_off)
        lamp = self.flatlamp.lamp_done.wait(timeout=60)
        if not lamp:
            return False
        self.flats_done.set()
        return True
        
    def take_darks(self, ticket):
        """
        Description
        -----------
        Takes dark images for a target.

        Parameters
        ----------
        ticket : ObservationTicket Object.
            Created by json_reader and object_reader.

        Returns
        -------
        bool
            True if successful, otherwise False.

        """
        self.darks_done.clear()
        filt = ticket.filter
        if type(filt) is str:
            filters = [filt]
        elif type(filt) is list:
            filters = filt
        else:
            logging.error('Filter argument is wrong type')
            return
        try:
            os.mkdir(os.path.join(self.image_directory, 'Darks_{}'.format(ticket.name)))
        except:
            logging.warning('Could not create dark folder, or folder already exists...')
        check = True
        for f in filters:
            for j in range(10):
                image_name = 'Dark_{0:d}s-{1:04d}.fits'.format(self.filter_exp_times[f], j + 1)
                self.camera.onThread(self.camera.expose, self.filter_exp_times[f], 0,
                                     save_path=os.path.join(self.image_directory, r'Darks_{}'.format(ticket.name),
                                                            image_name), type='dark')
                self.camera.image_done.wait()
            if self.filter_exp_times[f] == ticket.exp_time:
                check = False
        if check:
            for k in range(10):
                image_name = 'Dark_{0:d}s-{1:04d}.fits'.format(ticket.exp_time, k + 1)
                self.camera.onThread(self.camera.expose, ticket.exp_time, 0,
                                     save_path=os.path.join(self.image_directory, r'Darks_{}'.format(ticket.name),
                                                            image_name), type='dark')
                self.camera.image_done.wait()
        self.darks_done.set()
        return True
