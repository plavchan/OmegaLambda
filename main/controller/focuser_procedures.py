# Focusing procedures
import os
import logging
import time
import threading
import statistics

from .hardware import Hardware
from ..common.IO import config_reader
from ..common.util import filereader_utils

class FocusProcedures(Hardware):            #Subclassed from hardware
    
    def __init__(self, focus_obj, camera_obj):
        '''

        Parameters
        ----------
        focus_obj : CLASS INSTANCE OBJECT of Focuser
            From custom focuser class.
        camera_obj : CLASS INSTANCE OBJECT of Camera
            From custom camera class.

        Returns
        -------
        None.

        '''
        self.focuser = focus_obj
        self.camera = camera_obj
        self.config_dict = config_reader.get_config()
       
        self.focused = threading.Event()
        self.continuous_focusing = threading.Event()
        super(FocusProcedures, self).__init__(name='FocusProcedures')

    def StartupFocusProcedure(self, exp_time, filter, image_path):
        '''
        Description
        -----------
        Automated focusing procedure to be used before taking any science images.  Uses the
        camera to take test exposures and measures the FWHM of the images.
        
        Parameters
        ----------
        exp_time : INT
            Length of camera exposures in seconds.
        filter : STR
            Filter to take camera exposures in.
        image_path : STR
            File path to the CCD images to be used for focusing.
            
        Returns
        -------
        None.
        
        '''
        self.focused.clear()
        
        try: os.mkdir(os.path.join(image_path, r'focuser_calibration_images'))
        except: logging.error('Could not create subdirectory for focusing images, or directory already exists...')
        # Creates new sub-directory for focuser images
        self.focuser.onThread(self.focuser.setFocusDelta, self.config_dict.initial_focus_delta)
        self.focuser.onThread(self.focuser.current_position)
        time.sleep(2)
        initial_position = self.focuser.position
        Last_FWHM = None
        minimum = None
        i = 0
        j = 0
        while True:
            if self.camera.crashed.isSet() or self.focuser.crashed.isSet():
                logging.error('The camera or focuser has crashed...focus procedures cannot continue.')
                break
            image_name = '{0:s}_{1:d}s-{2:04d}.fits'.format('FocuserImage', exp_time, i + 1)
            path = os.path.join(image_path, r'focuser_calibration_images', image_name)
            self.camera.onThread(self.camera.expose, exp_time, filter, save_path=path, type="light")
            self.camera.image_done.wait()
            self.focuser.onThread(self.focuser.current_position)
            time.sleep(2)
            current_position = self.focuser.position
            FWHM = filereader_utils.Radial_Average(path, self.config_dict.saturation)
            if abs(current_position - initial_position) >= self.config_dict.focus_max_distance:
                logging.error('Focuser has stepped too far away from initial position and could not find a focus.')
                break
            if minimum != None and abs(FWHM - minimum) < self.config_dict.long_focus_tolerance:
                break
            if not FWHM:
                logging.warning('Could not retrieve FWHM from the last exposure...retrying')
                j += 1
                if j >= 3:
                    logging.error('There is a problem with MaxIm DL\'s fwhm property.  Cannot focus.')
                    break
                continue
            if Last_FWHM == None:
                # First cycle
                self.focuser.onThread(self.focuser.focusAdjust, "in")
                self.focuser.adjusting.wait()
                self.focuser.onThread(self.focuser.focusAdjust, "in")
                self.focuser.adjusting.wait()
                last = "in"
            
            elif abs(FWHM - Last_FWHM) <= 3:
                # Focus noise control -- If less than 3 pixels different (about 1"), it will keep moving in that direction and check again vs. the previous last_FWHM
                self.focuser.onThread(self.focuser.focusAdjust, last)
                self.focuser.adjusting.wait()
                i += 1
                continue
            elif FWHM <= Last_FWHM:
                # Better FWHM -- Keep going
                self.focuser.onThread(self.focuser.focusAdjust, last)
                self.focuser.adjusting.wait()
            elif FWHM > Last_FWHM:
                # Worse FWHM -- Switch directions
                if i > 1:
                    minimum = Last_FWHM
                if last == "in":
                    self.focuser.onThread(self.focuser.focusAdjust, "out")
                    self.focuser.adjusting.wait()
                    last = "out"
                elif last == "out":
                    self.focuser.onThread(self.focuser.focusAdjust, "in")
                    self.focuser.adjusting.wait()
                    last = "in"
            Last_FWHM = FWHM
            i += 1
        
        logging.info('Autofocus achieved a FWHM of {} pixels!'.format(FWHM))
        
        self.focused.set()
        return FWHM
    
    def ConstantFocusProcedure(self, initial_fwhm, image_path):
        '''
        Description
        -----------
        Automated focusing procedure to be used while taking science images.

        Parameters
        ----------
        initial_fwhm : FLOAT
            The fwhm achieved on the target by the startup focus procedure.
        image_path : STR
            File path to image folder.
        
        Returns
        -------
        None.

        '''
        # Will be constantly running in the background
        self.continuous_focusing.set()
        move = 'in'
        while self.continuous_focusing.isSet() and (self.camera.crashed.isSet() == False and self.focuser.crashed.isSet() == False):
            logging.debug('Continuous focusing procedure is active...')
            self.camera.image_done.wait()
            images = os.listdir(image_path)
            paths = []
            for fname in images:
                full_path = os.path.join(image_path, fname)
                if os.path.isfile(full_path): paths.append(full_path)
                else: continue
            newest_image = max(paths, key=os.path.getctime)
            fwhm = filereader_utils.Radial_Average(newest_image, self.config_dict.saturation)
            if abs(fwhm - initial_fwhm) >= self.config_dict.quick_focus_tolerance:
                self.focuser.onThread(self.focuser.focusAdjust, move)
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
                self.focuser.onThread(self.focuser.focusAdjust, move)
                
    def StopConstantFocusing(self):
        '''
        Description
        -----------
        Stops the continuous focusing procedure that is used while taking images.

        Returns
        -------
        None.

        '''
        logging.debug('Stopping continuous focusing')
        self.continuous_focusing.clear()