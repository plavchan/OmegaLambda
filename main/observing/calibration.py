# Darks & Flats automation
import os
import threading
import logging

from ..common.IO import config_reader
from ..common.util import filereader_utils
from ..common.datatype import filter_wheel
from ..controller.hardware import Hardware


class Calibration(Hardware):
    
    def __init__(self, camera_obj, flatlamp_obj, image_directories):
        """
        Initializes the calibration module as a subclass of hardware.

        Parameters
        ----------
        camera_obj : Camera Object
            Initialized camera.
        flatlamp_obj : FlatLamp Object
            Initialized flat lamp.
        image_directories : LIST
            Paths to where image files are saved for each ticket.

        Returns
        -------
        None.

        """
        self.camera = camera_obj
        self.flatlamp = flatlamp_obj
        self.image_directories = image_directories
        self.filterwheel_dict = filter_wheel.get_filter().filter_position_dict()
        self.filter_exp_times = {'clr': 3.0, 'uv': 120.0, 'b': 120.0, 'v': 16.0, 'r': 8.0, 'ir': 10.0, 'Ha': 120.0}
        self.config_dict = config_reader.get_config()
        
        self.flats_done = threading.Event()
        self.darks_done = threading.Event()
        super(Calibration, self).__init__(name='Calibration')

    def _class_connect(self):
        """
        Description
        -----------
        Overwrites base not implemented method.  However, nothing is necessary for the guider specifically,
        so the method just passes.

        Returns
        -------
        True : BOOL
        """
        return True
        
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
        # ticket.filter should be either a string or a list of strings
        filters = ticket.filter if type(ticket.filter) is list \
            else [ticket.filter] if type(ticket.filter) is str else None
        if not filters:
            logging.error('Wrong data type for filter(s) argument')
            return False
        if not os.path.exists(os.path.join(self.image_directories[ticket], 'Flats_{}'.format(ticket.name))):
            os.mkdir(os.path.join(self.image_directories[ticket], 'Flats_{}'.format(ticket.name)))
        else:
            logging.info('Flat folder already exists!  Assuming they have been collected, & aborting flat collection.')
            self.flatlamp.onThread(self.flatlamp.turn_off)
            self.flatlamp.lamp_done.wait(timeout=60)
            self.flats_done.set()
            return True
        for f in filters:
            j = 0
            scaled = False
            while j < self.config_dict.calibration_num:
                image_name = 'Flat_{0:.3f}s_{1:s}-{2:04d}.fits'.format(self.filter_exp_times[f], str(f).upper(), j + 1)
                if scaled:
                    image_name = image_name.replace('.fits', '-final.fits')
                self.camera.onThread(self.camera.expose, self.filter_exp_times[f], self.filterwheel_dict[f], 
                                     save_path=os.path.join(self.image_directories[ticket],
                                                            r'Flats_{}'.format(ticket.name),
                                                            image_name), type='light')
                self.camera.image_done.wait()
                median = filereader_utils.mediancounts(os.path.join(
                    self.image_directories[ticket], r'Flats_{}'.format(ticket.name), image_name))
                if scaled is False and median < self.config_dict.saturation:
                    # Calculate exposure time
                    desired = 15000
                    scale_factor = desired/median
                    self.filter_exp_times[f] *= scale_factor
                    if self.filter_exp_times[f] <= 0.001:
                        self.filter_exp_times[f] = 0.001
                    scaled = True
                elif j == 0 and median >= self.config_dict.saturation:
                    self.filter_exp_times[f] = self.filter_exp_times[f]/2
                    if self.filter_exp_times[f] <= 0.001:
                        self.filter_exp_times[f] = 0.001
                        scaled = True
                else:
                    j += 1
        files = os.listdir(os.path.join(self.image_directories[ticket], 'Flats_{}'.format(ticket.name)))
        for file in files:
            file = os.path.join(self.image_directories[ticket], 'Flats_{}'.format(ticket.name), file)
            if 'final' not in str(file):
                os.remove(file)
        logging.info('Test flats removed!')
        self.flatlamp.onThread(self.flatlamp.turn_off)
        self.flatlamp.lamp_done.wait(timeout=60)
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
        filters = ticket.filter if type(ticket.filter) is list \
            else [ticket.filter] if type(ticket.filter) is str else None
        if not filters:
            logging.error('Wrong data type for filter(s) argument')
            return False
        exp_times = ticket.exp_time if type(ticket.exp_time) is list \
            else [ticket.exp_time] if type(ticket.exp_time) in (int, float) else None
        if not exp_times:
            logging.error('Wrong data type for exp_time(s) argument')
            return False
        if not os.path.exists(os.path.join(self.image_directories[ticket], 'Darks_{}'.format(ticket.name))):
            os.mkdir(os.path.join(self.image_directories[ticket], 'Darks_{}'.format(ticket.name)))
        else:
            logging.info('Dark folder already exists!  Assuming they have been collected, & aborting dark collection...')
            self.darks_done.set()
            return True
        for f in filters:
            for j in range(self.config_dict.calibration_num):
                image_name = 'Dark_{0:.3f}s-{1:04d}.fits'.format(self.filter_exp_times[f], j + 1)
                match = False
                for name in os.listdir(os.path.join(self.image_directories[ticket], 'Darks_{}'.format(ticket.name))):
                    if name == image_name:
                        match = True
                if match:
                    continue
                self.camera.onThread(self.camera.expose, self.filter_exp_times[f], 4,
                                     save_path=os.path.join(self.image_directories[ticket], r'Darks_{}'.format(ticket.name),
                                                            image_name), type='dark')
                self.camera.image_done.wait()

        for exp_time in exp_times:
            for k in range(self.config_dict.calibration_num):
                image_name = 'Dark_{0:.3f}s-{1:04d}.fits'.format(exp_time, k + 1)
                match = False
                for name in os.listdir(os.path.join(self.image_directories[ticket], 'Darks_{}'.format(ticket.name))):
                    if name == image_name:
                        match = True
                if match:
                    continue
                self.camera.onThread(self.camera.expose, exp_time, 4,
                                     save_path=os.path.join(self.image_directories[ticket],
                                                            r'Darks_{}'.format(ticket.name),
                                                            image_name), type='dark')
                self.camera.image_done.wait()
        self.darks_done.set()
        return True
