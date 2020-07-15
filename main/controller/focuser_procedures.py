# Focusing procedures
import os
import logging
import time
import threading
import statistics
import numpy as np
import matplotlib.pyplot as plt

from .hardware import Hardware
from ..common.IO import config_reader
from ..common.util import filereader_utils


class FocusProcedures(Hardware):
    
    def __init__(self, focus_obj, camera_obj):
        """
        Initializes focusprocedures as a subclass of hardware.

        Parameters
        ----------
        focus_obj : CLASS INSTANCE OBJECT of Focuser
            From custom focuser class.
        camera_obj : CLASS INSTANCE OBJECT of Camera
            From custom camera class.

        Returns
        -------
        None.

        """
        self.focuser = focus_obj
        self.camera = camera_obj
        self.config_dict = config_reader.get_config()
        self.FWHM = None
       
        self.focused = threading.Event()
        self.continuous_focusing = threading.Event()
        super(FocusProcedures, self).__init__(name='FocusProcedures')

    def startup_focus_procedure(self, exp_time, _filter, image_path):
        """
        Description
        -----------
        Automated focusing procedure to be used before taking any science images.  Uses the
        camera to take test exposures and measures the FWHM of the images.

        Parameters
        ----------
        exp_time : INT
            Length of camera exposures in seconds.
        _filter : STR
            Filter to take camera exposures in.
        image_path : STR
            File path to the CCD images to be used for focusing.

        Returns
        -------
        None.

        """
        self.focused.clear()
        
        try:
            os.mkdir(os.path.join(image_path, r'focuser_calibration_images'))
        except:
            logging.error('Could not create subdirectory for focusing images, or directory already exists...')
        # Creates new sub-directory for focuser images
        self.focuser.onThread(self.focuser.set_focus_delta, self.config_dict.initial_focus_delta)
        self.focuser.onThread(self.focuser.current_position)
        time.sleep(2)
        initial_position = self.focuser.position
        minimum = None
        last = None
        fwhm = None
        i = 0
        j = 0
        last_fwhm = None
        fwhm_values = []
        focus_positions = []
        while True:
            if self.camera.crashed.isSet() or self.focuser.crashed.isSet():
                logging.error('The camera or focuser has crashed...focus procedures cannot continue.')
                break
            image_name = '{0:s}_{1:d}s-{2:04d}.fits'.format('FocuserImage', exp_time, i + 1)
            path = os.path.join(image_path, r'focuser_calibration_images', image_name)
            self.camera.onThread(self.camera.expose, exp_time, _filter, save_path=path, type="light")
            self.camera.image_done.wait()
            self.focuser.onThread(self.focuser.current_position)
            time.sleep(2)
            current_position = self.focuser.position
            fwhm = filereader_utils.radial_average(path, self.config_dict.saturation)
            if abs(current_position - initial_position) >= self.config_dict.focus_max_distance:
                logging.error('Focuser has stepped too far away from initial position and could not find a focus.')
                break
            if fwhm is None:
                logging.warning('No fwhm could be calculated...trying again')
                continue
            if minimum is not None and abs(fwhm - minimum) < self.config_dict.long_focus_tolerance:
                break
            if not fwhm:
                logging.warning('Could not retrieve FWHM from the last exposure...retrying')
                j += 1
                if j >= 3:
                    logging.error('There is a problem with MaxIm DL\'s fwhm property.  Cannot focus.')
                    break
                continue
            if i == 0:
                # First cycle
                self.focuser.onThread(self.focuser.focus_adjust, "in")
                self.focuser.adjusting.wait()
                self.focuser.onThread(self.focuser.focus_adjust, "in")
                self.focuser.adjusting.wait()
                last = "in"
            
            elif abs(fwhm - last_fwhm) <= 1:
                # Focus noise control -- If less than 1 pixel different (about 0.35"), it will keep moving in
                # that direction and check again vs. the previous last_fwhm
                self.focuser.onThread(self.focuser.focus_adjust, last)
                self.focuser.adjusting.wait()
                i += 1
                continue
            elif fwhm <= last_fwhm:
                # Better FWHM -- Keep going
                self.focuser.onThread(self.focuser.focus_adjust, last)
                self.focuser.adjusting.wait()
            elif fwhm > last_fwhm:
                # Worse FWHM -- Switch directions
                if i > 1:
                    minimum = last_fwhm
                if last == "in":
                    self.focuser.onThread(self.focuser.focus_adjust, "out")
                    self.focuser.adjusting.wait()
                    last = "out"
                elif last == "out":
                    self.focuser.onThread(self.focuser.focus_adjust, "in")
                    self.focuser.adjusting.wait()
                    last = "in"
            last_fwhm = fwhm
            fwhm_values.append(fwhm)
            focus_positions.append(current_position)
            i += 1
        
        data = sorted(zip(focus_positions, fwhm_values))
        x = [_[0] for _ in data]
        y = [_[1] for _ in data]
        med = statistics.median(x)
        fit = np.polyfit(x, y, 2)
        xfit = np.linspace(med - 50, med + 50, 100)
        yfit = fit[0]*(xfit**2) + fit[1]*xfit + fit[2]
        plt.plot(x, y, 'bo', label='Raw data')
        plt.plot(xfit, yfit, 'r-', label='Parabolic fit')
        plt.legend()
        plt.xlabel('Focus Positions (units)')
        plt.ylabel('FWHM value (pixels)')
        plt.savefig(os.path.join(self.config_dict.home_directory, r'test/FocusPlot.png'))
        
        minindex = np.where(yfit == min(yfit))
        minfocus = np.round(xfit[minindex])
        logging.info('Autofocus achieved a FWHM of {} pixels!'.format(fwhm))
        logging.info('The theoretical minimum focus was calculated to be at position {}'.format(minfocus))
        
        self.focused.set()
        self.FWHM = fwhm
    
    def constant_focus_procedure(self, image_path):
        """
        Description
        -----------
        Automated focusing procedure to be used while taking science images.

        Parameters
        ----------
        image_path : STR
            File path to image folder.

        Returns
        -------
        None.

        """
        # Will be constantly running in the background
        self.continuous_focusing.set()
        move = 'in'
        while self.continuous_focusing.isSet() and (self.camera.crashed.isSet() is False
                                                    and self.focuser.crashed.isSet() is False):
            logging.debug('Continuous focusing procedure is active...')
            self.camera.image_done.wait()
            images = os.listdir(image_path)
            paths = []
            for fname in images:
                full_path = os.path.join(image_path, fname)
                if os.path.isfile(full_path):
                    paths.append(full_path)
                else:
                    continue
            newest_image = max(paths, key=os.path.getctime)
            fwhm = filereader_utils.radial_average(newest_image, self.config_dict.saturation)
            if not self.FWHM:
                self.FWHM = fwhm
            if abs(fwhm - self.FWHM) >= self.config_dict.quick_focus_tolerance:
                self.focuser.onThread(self.focuser.focus_adjust, move)
                self.focuser.adjusting.wait()
            else:
                continue
            
            self.camera.image_done.wait()
            self.camera.onThread(self.camera.get_FWHM)
            time.sleep(1)
            next_fwhm = self.camera.fwhm
            if next_fwhm <= fwhm:
                continue
            elif next_fwhm > fwhm:
                move = 'out'
                self.focuser.onThread(self.focuser.focus_adjust, move)
                
    def stop_constant_focusing(self):
        """
        Description
        -----------
        Stops the continuous focusing procedure that is used while taking images.

        Returns
        -------
        None.

        """
        logging.debug('Stopping continuous focusing')
        self.continuous_focusing.clear()
