# Focusing procedures
import os
import sys
import logging
import time
import threading
import statistics
import msvcrt
import numpy as np
import matplotlib.pyplot as plt

from .hardware import Hardware
from ..common.IO import config_reader
from ..common.util import filereader_utils


class FocusProcedures(Hardware):

    startup_focuses = 0

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
        
        if not os.path.exists(os.path.join(image_path, r'focuser_calibration_images')):
            os.mkdir(os.path.join(image_path, r'focuser_calibration_images'))
        # Creates new sub-directory for focuser images
        self.focuser.onThread(self.focuser.set_focus_delta, self.config_dict.initial_focus_delta)
        self.focuser.onThread(self.focuser.current_position)
        time.sleep(2)
        initial_position = self.focuser.position
        fwhm = None
        fwhm_values = []
        focus_positions = []
        i = 0
        errors = 0
        while i < 10:
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
            if not fwhm:
                logging.warning('No fwhm could be calculated...trying again')
                errors += 1
                if errors < 3:
                    continue
                else:
                    logging.critical('Cannot focus on target')
                    break
            self.focuser.onThread(self.focuser.set_focus_delta, self.config_dict.initial_focus_delta)
            if i < 5:
                if i == 0:
                    self.focuser.onThread(self.focuser.set_focus_delta, self.config_dict.initial_focus_delta*2)
                self.focuser.onThread(self.focuser.focus_adjust, "in")
                self.focuser.adjusting.wait()
            elif i == 5:
                self.focuser.onThread(self.focuser.absolute_move,
                                      int(initial_position + self.config_dict.initial_focus_delta*2))
                self.focuser.adjusting.wait()
            elif i > 5:
                self.focuser.onThread(self.focuser.focus_adjust, "out")
                self.focuser.adjusting.wait()
            logging.debug('Found fwhm={} for the last image'.format(fwhm))
            fwhm_values.append(fwhm)
            focus_positions.append(current_position)
            i += 1
        FocusProcedures.startup_focuses += 1
        
        data = sorted(zip(focus_positions, fwhm_values))
        x = [_[0] for _ in data]
        y = [_[1] for _ in data]
        xfit = None
        yfit = None
        if len(x) >= 3 and len(y) >= 3:
            med = statistics.median(x)
            fit = np.polyfit(x, y, 2)
            xfit = np.linspace(med - 50, med + 50, 100)
            yfit = fit[0]*(xfit**2) + fit[1]*xfit + fit[2]
            fig, ax = plt.subplots()
            ax.plot(x, y, 'bo', label='Raw data')
            ax.plot(xfit, yfit, 'r-', label='Parabolic fit')
            ax.legend()
            ax.set_xlabel('Focus Positions (units)')
            ax.set_ylabel('FWHM value (pixels)')
            ax.set_title('Focus Positions Graph')
            ax.grid()
            plt.savefig(os.path.join(self.config_dict.home_directory, r'test/FocusPlot.png'))
        elif FocusProcedures.startup_focuses <= 1:
            try:
                answer = self.input_with_timeout(
                    "Focuser has failed to produce a good parabolic fit.  Would you like to try again? (y/n) \n"
                    "You have 30 seconds to answer; on timeout the program will automatically refocus: ", 30
                )
                if answer == 'y':
                    self.startup_focus_procedure(exp_time, _filter, image_path)
                elif answer == 'n':
                    self.focuser.onThread(self.focuser.absolute_move, initial_position)
                    self.focuser.adjusting.wait()
                else:
                    print('Invalid answer...')
                    self.focuser.onThread(self.focuser.absolute_move, initial_position)
                    self.focuser.adjusting.wait()
            except TimeoutExpired:
                self.focuser.onThread(self.focuser.absolute_move, initial_position)
                self.focuser.adjusting.wait()
            return

        minindex = np.where(yfit == min(yfit))
        if (minindex == np.where(yfit == yfit[0])) or (minindex == np.where(yfit == yfit[-1])):
            logging.warning('Parabolic fit has failed and fit an incorrect parabola.  Cannot calculate minimum focus.')
            self.focuser.onThread(self.focuser.absolute_move, initial_position)
            self.focuser.adjusting.wait()
        else:
            minfocus = np.round(xfit[minindex])
            logging.info('Autofocus achieved a FWHM of {} pixels!'.format(fwhm))
            logging.info('The theoretical minimum focus was calculated to be at position {}'.format(minfocus))
            if abs(initial_position - minfocus) <= self.config_dict.focus_max_distance:
                self.focuser.onThread(self.focuser.absolute_move, minfocus)
            else:
                logging.info('Calculated minimum focus is out of range of the focuser movement restrictions. '
                             'This is probably due to an error in the calculations.')
                self.focuser.onThread(self.focuser.absolute_move, initial_position)
                self.focuser.adjusting.wait()
        self.focused.set()
        self.FWHM = fwhm
        return
    
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
            newest_image = self.get_newest_image(image_path)
            fwhm = filereader_utils.radial_average(newest_image, self.config_dict.saturation)
            if not self.FWHM:
                self.FWHM = fwhm
            if not fwhm:
                logging.debug('Constant focusing could not find a fwhm for the recent image.  Skipping...')
                continue
            if abs(fwhm - self.FWHM) >= self.config_dict.quick_focus_tolerance:
                self.focuser.onThread(self.focuser.focus_adjust, move)
                self.focuser.adjusting.wait()
            else:
                continue
            
            self.camera.image_done.wait()
            newest_image = self.get_newest_image(image_path)
            next_fwhm = filereader_utils.radial_average(newest_image, self.config_dict.saturation)
            if not next_fwhm or not fwhm:
                logging.debug('Constant focusing could not find a fwhm for the recent image.  Skipping...')
                continue
            if next_fwhm <= fwhm:
                continue
            elif next_fwhm > fwhm:
                move = 'out'
                self.focuser.onThread(self.focuser.focus_adjust, move)

    @staticmethod
    def get_newest_image(image_path):
        """

        Parameters
        ----------
        image_path : STR
            File path to the images being saved by the camera.

        Returns
        -------
        newest_image : STR
            Full path to the most recently created image file in the given directory.
        """
        images = os.listdir(image_path)
        paths = []
        for fname in images:
            full_path = os.path.join(image_path, fname)
            if os.path.isfile(full_path):
                paths.append(full_path)
            else:
                continue
        newest_image = max(paths, key=os.path.getctime)
        return newest_image

    @staticmethod
    def input_with_timeout(prompt, timeout, timer=time.monotonic):
        """

        Parameters
        ----------
        prompt : STR
            Input prompt to give the user
        timeout : INT or FLOAT
            Time in seconds the user has to give a response
        timer : time.monotonic
            Timer object from time module

        Returns
        -------
        msvcrt.getwche()
            A single character typed by the user -- meant to be user for 'y' / 'n' responses.
            If the user does not type anything, a special TimeoutExpired exception is raised.
        """
        sys.stdout.write(prompt)
        sys.stdout.flush()
        endtime = timer() + timeout
        while timer() < endtime:
            if msvcrt.kbhit():
                return msvcrt.getwche()
            time.sleep(0.04)
        raise TimeoutExpired

    def stop_constant_focusing(self):
        """
        Description
        -----------
        Stops the continuous focusing procedure that is used while taking images.
        Must NOT be called with onThread, otherwise the focuser will be stuck on constant focusing on won't ever get
        to execute stop.

        Returns
        -------
        None.

        """
        logging.debug('Stopping continuous focusing')
        self.continuous_focusing.clear()


class TimeoutExpired(Exception):
    """
    Description
    -----------
    To be used only for input_with_timeout.  An exception that does not stop/prevent any threads or the main thread
    from running, and is just used to check if the input has timed out or not.
    """
    pass
