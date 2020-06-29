# Focusing procedures
import os
import logging
import time
import threading

from .hardware import Hardware

class FocusProcedures(Hardware):
    
    def __init__(self, camera_obj):
        self.camera = camera_obj
       
        self.focused = threading.Event()
        super(FocusProcedures, self).__init__(name='FocusProcedures')

    def StartupFocusProcedure(self, exp_time, filter, starting_delta, image_path, long_focus_tolerance, max_distance):
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
        starting_delta : INT
            Initial focuser movement length.
        image_path : STR
            File path to the CCD images to be used for focusing.
        long_focus_tolerance : INT
            How close the focus should be to the minimum found before stopping.
        max_distance : INT
            Maximum distance away from the initial position the focuser may move before stopping.

        Returns
        -------
        None.
        
        '''
        self.focused.clear()
        
        try: os.mkdir(os.path.join(image_path, r'focuser_calibration_images'))
        except: logging.error('Could not create subdirectory for focusing images, or directory already exists...')
        # Creates new sub-directory for focuser images
        self.focuser.setFocusDelta(starting_delta)
        initial_position = self.focuser.current_position()
        Last_FWHM = None
        minimum = None
        i = 0
        while True:
            image_name = '{0:s}_{1:d}s-{2:04d}.fits'.format('FocuserImage', exp_time, i + 1)
            path = os.path.join(image_path, r'focuser_calibration_images', image_name)
            self.camera.onThread(self.camera.expose, exp_time, filter, save_path=path, type="light")
            self.camera.image_done.wait()
            current_position = self.focuser.current_position()
            time.sleep(1)
            self.camera.onThread(self.camera.get_FWHM)
            time.sleep(1)
            FWHM = self.camera.fwhm
            if abs(current_position - initial_position) >= max_distance:
                logging.error('Focuser has stepped too far away from initial position and could not find a focus.')
                break
            if minimum != None and abs(FWHM - minimum) < long_focus_tolerance:
                break
            if not FWHM:
                logging.warning('Could not retrieve FWHM from the last exposure...retrying')
                i += 1
                if i >= 9:
                    logging.error('There is a problem with MaxIm DL\'s fwhm property.  Cannot focus.')
                    break
                continue
            if Last_FWHM == None:
                # First cycle
                self.focuser.focusAdjust("in")
                self.focuser.focusAdjust("in")
                last = "in"
            
            # Intelligence for focus noise?
                
            elif FWHM <= Last_FWHM:
                # Better FWHM -- Keep going
                self.focuser.focusAdjust(last)
            elif FWHM > Last_FWHM:
                # Worse FWHM -- Switch directions
                if i > 1:
                    minimum = Last_FWHM
                if last == "in":
                    self.focuser.focusAdjust("out")
                    last = "out"
                elif last == "out":
                    self.focuser.focusAdjust("in")
                    last = "in"
            Last_FWHM = FWHM
            i += 1
        
        logging.info('Autofocus achieved a FWHM of {} pixels!'.format(FWHM))
        
        self.focused.set()
        return FWHM
    
    def ConstantFocusProcedure(self, initial_fwhm, quick_focus_tolerance):
        # Will be constantly running in the background
        move = 'in'
        while True:
            self.focuser.onThread(self.camera.image_done.wait)
            self.camera.onThread(self.camera.get_FWHM)
            time.sleep(1)
            if abs(self.camera.fwhm - initial_fwhm) >= quick_focus_tolerance:
                self.focuser.onThread(self.focuser.focusAdjust, move)
                
    def disconnect(self):
        self.focuser.disconnect()