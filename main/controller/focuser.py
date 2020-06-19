import logging

from main.controller.hardware import Hardware

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
        
    def AutoFocusProcedure(self, exp_time, filter, starting_delta, loops):
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

        Returns
        -------
        None.

        '''
        self.setFocusDelta(starting_delta)
        Last_FWHM = None
        for i in range(loops):
            self.camera.onThread(self.camera.expose, exp_time, filter)
            self.camera.image_done.wait()
            # Use Owen's filereader here to get star FWHM
            FWHM = None
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
        if FWHM <= 10:
            logging.info('Autofocus achieved a FWHM of less than 10 arcseconds!')
        elif FWHM <= 15:
            logging.info('Autofocus achieved a FWHM of less than 15 arcseconds!')
        else:
            logging.info('Autofocus did not get to a FWHM of less than 15 arcseconds.')
        
# Robofocus documentation: http://www.robofocus.com/documents/robofocusins31.pdf ?