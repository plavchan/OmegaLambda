# Focusing procedures
import os
import logging
import time
import threading
import numpy as np
import matplotlib.pyplot as plt

from .hardware import Hardware
from ..common.IO import config_reader
from ..common.util import filereader_utils


class FocusProcedures(Hardware):

    def __init__(self, focus_obj, camera_obj, conditions_obj):
        """
        Initializes focusprocedures as a subclass of hardware.

        Parameters
        ----------
        focus_obj : CLASS INSTANCE OBJECT of Focuser
            From custom focuser class.
        camera_obj : CLASS INSTANCE OBJECT of Camera
            From custom camera class.
        conditions_obj : CLASS INSTANCE OBJECT of Conditions
            From custom conditions class.

        Returns
        -------
        None.

        """
        self.focuser = focus_obj
        self.camera = camera_obj
        self.conditions = conditions_obj
        self.config_dict = config_reader.get_config()
        self.position_previous = None
        self.temp_previous = None
       
        self.focused = threading.Event()
        self.continuous_focusing = threading.Event()
        super(FocusProcedures, self).__init__(name='FocusProcedures')

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

    def get_temperature(self):
        """
        Returns
        -------
        FLOAT or INT : The temperature value as read by the focuser class.
        """
        self.focuser.onThread(self.focuser.get_temperature)
        self.focuser.adjusting.wait()
        time.sleep(1)
        return self.focuser.temperature

    def startup_focus_procedure(self, exp_time, _filter, image_path):
        """
        Description
        -----------
        Automated focusing procedure to be used before taking any science images.  Uses the
        camera to take test exposures and measures the FWHM of the images.

        Parameters
        ----------
        exp_time : FLOAT or INT
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
        
        if not os.path.exists(os.path.join(image_path, r'focuser_images')):
            os.mkdir(os.path.join(image_path, r'focuser_images'))
        # Creates new sub-directory for focuser images
        self.focuser.onThread(self.focuser.current_position)
        self.focuser.adjusting.wait()
        time.sleep(2)
        initial_position = self.focuser.position
        fwhm_values = []
        focus_positions = []
        i = 0
        errors = 0
        crash_loops = 0
        while i < 11:
            if self.camera.crashed.isSet() or self.focuser.crashed.isSet():
                if crash_loops <= 4:
                    logging.warning('The camera or focuser has crashed...waiting for potential recovery.')
                    time.sleep(10)
                    crash_loops += 1
                    continue
                elif crash_loops > 4:
                    logging.error('The camera or focuser has still not recovered from crashing...focus procedures '
                                  'cannot continue.')
                    break
            image_name = '{0:s}_{1:.3f}s-{2:04d}.fits'.format('FocuserImage', exp_time, i + 1)
            path = os.path.join(image_path, r'focuser_calibration_images', image_name)
            self.camera.onThread(self.camera.expose, exp_time, _filter, save_path=path, type="light")
            self.camera.image_done.wait()
            time.sleep(2)
            self.focuser.onThread(self.focuser.current_position)
            self.camera.onThread(self.camera.get_fwhm)
            time.sleep(2)
            current_position = self.focuser.position
            fwhm = self.camera.fwhm if self.camera.fwhm else \
                filereader_utils.radial_average(path, self.config_dict.saturation)
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
            errors = 0      # This way it must be 3 in a row
            if i < 5:
                if i == 0:
                    self.focuser.onThread(self.focuser.move_in, self.config_dict.initial_focus_delta*2)
                    self.focuser.adjusting.wait(timeout=10)
                else:
                    self.focuser.onThread(self.focuser.move_in, self.config_dict.initial_focus_delta)
                    self.focuser.adjusting.wait(timeout=10)
            elif i == 5:
                self.focuser.onThread(self.focuser.absolute_move,
                                      int(initial_position + self.config_dict.initial_focus_delta*2))
                time.sleep(5)
                self.focuser.adjusting.wait(timeout=30)
            elif i > 5:
                self.focuser.onThread(self.focuser.move_out, self.config_dict.initial_focus_delta)
                self.focuser.adjusting.wait(timeout=10)
            logging.debug('Found fwhm = {} for the last image'.format(fwhm))
            fwhm_values.append(fwhm)
            focus_positions.append(current_position)
            i += 1
        
        data = sorted(zip(focus_positions, fwhm_values))
        x = [_[0] for _ in data]
        y = [_[1] for _ in data]
        if fit_status := (len(x) >= 3 and len(y) >= 3):
            med = np.median(x)
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
            current_path = os.path.abspath(os.path.dirname(__file__))
            target_path = os.path.abspath(os.path.join(current_path, r'../../test/FocusPlot.png'))
            plt.savefig(target_path)

            minindex = np.where(yfit == min(yfit))
            if (minindex == np.where(yfit == yfit[0])) or (minindex == np.where(yfit == yfit[-1])):
                fit_status = False
            else:
                minfocus = np.round(xfit[minindex])
                logging.info('The theoretical minimum focus was calculated to be at position {}'.format(minfocus))
                if abs(initial_position - minfocus) <= self.config_dict.focus_max_distance:
                    self.focuser.adjusting.wait(timeout=10)
                    self.focuser.onThread(self.focuser.absolute_move, minfocus)
                    self.focuser.adjusting.wait(timeout=30)
                else:
                    fit_status = False
        if not fit_status:
            logging.error('The focuser either couldn\'t fit a correct parabola to the data, or couldn\'t '
                          'move to the calculated minimum focus position.  Resetting to initial position.')
            self.focuser.adjusting.wait(timeout=10)
            self.focuser.onThread(self.focuser.absolute_move, initial_position)
            self.focuser.adjusting.wait(timeout=30)
        self.focused.set()
        self.focuser.onThread(self.focuser.current_position)
        time.sleep(2)
        self.temp_previous = self.get_temperature()
        self.position_previous = self.focuser.position
        return
    
    def constant_focus_procedure(self):
        """
        Description
        -----------
        Automated focusing procedure to be used while taking science images.

        Returns
        -------
        None.

        """
        # Will be constantly running in the background
        # Current focus position = initial focus position + 2 steps/degF * (Tcurrent - Tinitial)
        # Will check & adjust once every 30 minutes (adjustable)
        self.continuous_focusing.set()
        while self.continuous_focusing.isSet() and (self.camera.crashed.isSet() is False
                                                    and self.focuser.crashed.isSet() is False):
            time.sleep(self.config_dict.focus_adjust_frequency * 60)
            logging.debug('Continuous focusing procedure is alive...')
            temp_current = self.conditions.temperature
            if temp_current is None:
                continue
            if self.position_previous is None:
                self.focuser.onThread(self.focuser.current_position)
                time.sleep(2)
                self.position_previous = self.focuser.position
                continue
            if self.temp_previous is None:
                self.temp_previous = temp_current
                continue
            new_position = self.position_previous + \
                self.config_dict.focus_temperature_constant * (temp_current - self.temp_previous)
            pos_diff = int(new_position - self.position_previous)
            func = self.focuser.move_in if pos_diff < 0 else self.focuser.move_out if pos_diff > 0 else None
            if not func:
                self.temp_previous = temp_current
                self.position_previous = new_position
                continue
            self.focuser.onThread(func, abs(pos_diff))
            self.focuser.adjusting.wait(timeout=15)
            self.temp_previous = temp_current
            self.position_previous = new_position

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
        paths = [full_path for fname in images if os.path.isfile(full_path := os.path.join(image_path, fname))]
        newest_image = max(paths, key=os.path.getctime)
        return newest_image

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
