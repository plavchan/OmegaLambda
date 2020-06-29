import logging
import threading
import win32com.client
import time

class Focuser():    # NOT subclassed from hardware...instead FocusProcedures is.
    
    def __init__(self):
        '''

        Returns
        -------
        None.

        '''
        self.adjusting = threading.Event()
        self.Focuser = win32com.client.Dispatch("RoboFocus.FocusControl")
        self.check_connection()
        
    def check_connection(self):
        self.Focuser.actOpenComm()
        time.sleep(2)
        if self.Focuser.getCommStatus():
            print("Focuser has successfully connected")
        else:
            print("ERROR: Could not connect to focuser")
        
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
        
    def current_position(self):
        '''

        Returns
        -------
        INT
            Current position of the focuser.

        '''
        return self.Focuser.getPosition()

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
        self.adjusting.clear()
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
        self.adjusting.set()
            
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