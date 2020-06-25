import logging
import os
import threading
import time

from .hardware import Hardware
from ..common.util import filereader_utils

class Focuser(Hardware):
    
    def __init__(self, camera_obj):
        '''

        Parameters
        ----------
        camera_obj : CLASS INSTANCE OBJECT of Camera
            Camera object to be passed in via observation_run

        Returns
        -------
        None.

        '''
        self.camera = camera_obj
        self.focused = threading.Event()
        super(Focuser, self).__init__(name='Focuser')       # Calls Hardware.__init__ with the name 'Focuser'
        
    def setFocusDelta(self, amount):
        '''

        Parameters
        ----------
        amount : INT
            Value to set default focuser move length.

        Returns
        -------
        None.

        '''
        self.Focuser.setDelta(int(amount))
        logging.debug('Focuser delta changed')

    def focusAdjust(self, direction, amount=None):
        '''

        Parameters
        ----------
        direction : STR
            "in" or "out" to specify direction of focuser move.
        amount : INT, optional
            Value to change default focuser move length. The default is None, which
            keeps it as it was before.

        Returns
        -------
        None.

        '''
        if amount != None:
            self.setFocusDelta(amount)
        if direction == "in":
            self.Focuser.actIn()
            logging.info('Focuser moved in')
        elif direction == "out":
            self.Focuser.actOut()
            logging.info('Focuser moved out')
        else:
            logging.error('Invalid focus move direction')
            
    def AbsoluteMove(self, position):
        '''

        Parameters
        ----------
        position : INT
            Absolute position to move the focuser to.

        Returns
        -------
        None.

        '''
        self.Focuser.actGoToPosition(int(position))
        
    def AbortFocusMove(self):
        '''
        Description
        -----------
        Stops any focuser movements that may be in progress.

        Returns
        -------
        None.

        '''
        self.Focuser.actStop()
        
    def AutoFocusProcedure(self, exp_time, filter, starting_delta, loops, image_path, focus_goal):
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
        loops : INT
            How many exposures to take before settling on a focus.
        image_path : STR
            File path to the CCD images to be used for focusing.
        focus_goal : INT
            Goal for how good to get the focus, in arcseconds.

        Returns
        -------
        None.

        '''
        self.focused.clear()
        
        try: os.mkdir(os.path.join(image_path, r'focuser_calibration_images'))
        except: logging.error('Could not create subdirectory for focusing images, or directory already exists...')
        # Creates new sub-directory for focuser images
        self.setFocusDelta(starting_delta)
        Last_FWHM = None
        for i in range(loops):
            image_name = '{0:s}_{1:d}s-{2:04d}.fits'.format('FocuserImage', exp_time, i + 1)
            path = os.path.join(image_path, r'focuser_calibration_images', image_name)
            self.camera.onThread(self.camera.expose, exp_time, filter, save_path=path, type="light")
            self.camera.image_done.wait()
            FWHM = self.camera.onThread(self.camera.get_FWHM)
            if not FWHM:
                logging.warning('Could not retrieve FWHM from the last exposure...retrying')
                continue
            if FWHM <= focus_goal: #TODO: Convert focus goal from arcseconds to pixels
                break
            if Last_FWHM == None:
                # First cycle
                self.focusAdjust("in"); last = "in"
            elif FWHM <= Last_FWHM:
                # Better FWHM -- Keep going
                self.focusAdjust(last)
            elif FWHM > Last_FWHM:
                # Worse FWHM -- Switch directions
                if last == "in":
                    self.focusAdjust("out"); last = "out"
                elif last == "out":
                    self.focusAdjust("in"); last = "in"
            
            Last_FWHM = FWHM
            if i == 9:
                self.setFocusDelta(int(starting_delta/2))
            if i == 19:
                self.setFocusDelta(int(starting_delta/4))
        logging.info('Autofocus achieved a FWHM of {} pixels!'.format(FWHM))
        
        self.focused.set()
        
    def disconnect(self):
        '''
        Description
        -----------
        Disconnects from RoboFocus

        Returns
        -------
        None.

        '''
        self.Focuser.actCloseComm()
        
# Robofocus documentation: http://www.robofocus.com/documents/robofocusins31.pdf