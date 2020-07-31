import logging
import threading
import time

from .hardware import Hardware


class Focuser(Hardware):
    
    def __init__(self):
        """
        Initializes the focuser as a subclass of hardware.

        Returns
        -------
        None.

        """
        self.adjusting = threading.Event()
        self.position = None
        super(Focuser, self).__init__(name='Focuser')      # calls Hardware.__init__ with the name 'focuser'

    def check_connection(self):
        """
        Description
        -----------
        Overwrites base class.  Checks for focuser connection specifically.

        Returns
        -------

        """
        logging.info('Checking connection for the {}'.format(self.label))
        self.live_connection.clear()
        self.Focuser.actOpenComm()
        time.sleep(2)
        if self.Focuser.getCommStatus():
            print("Focuser has successfully connected")
            self.live_connection.set()
        else:
            logging.error("Could not connect to focuser")

    def set_focus_delta(self, amount):
        """

        Parameters
        ----------
        amount : INT
            Value to set default focuser move length.

        Returns
        -------
        bool
            True if successful, otherwise False.

        """
        if not self.crashed.isSet():
            self.Focuser.setDelta(int(amount))
            logging.debug('Focuser delta changed')
            return True
        else:
            logging.warning('Focuser has crashed...cannot set focus delta at this time')
            return False
        
    def current_position(self):
        """
        Description
        -----------
        Sets a property equal to the current position of the focuser.
        Cannot be directly called due to threading.

        Returns
        -------
        None

        """
        self.position = self.Focuser.getPosition()

    def focus_adjust(self, direction, amount=None):
        """

        Parameters
        ----------
        direction : STR
            "in" or "out" to specify direction of focuser move.
        amount : INT, optional
            Value to change default focuser move length. The default is None, which
            keeps it as it was before.

        Returns
        -------
        bool
            True if successful, otherwise False.

        """
        if not self.crashed.isSet():
            self.adjusting.clear()
            if amount is not None:
                self.set_focus_delta(amount)
            if direction == "in":
                self.Focuser.actIn()
                logging.info('Focuser moved in')
            elif direction == "out":
                self.Focuser.actOut()
                logging.info('Focuser moved out')
            else:
                logging.error('Invalid focus move direction')
            self.adjusting.set()
        else:
            logging.warning('Focuser has crashed...cannot adjust focus position at this time')
            return False
        return True

    def absolute_move(self, position):
        """

        Parameters
        ----------
        position : INT
            Absolute position to move the focuser to.

        Returns
        -------
        bool
            True if successful, otherwise False.

        """
        if not self.crashed.isSet():
            self.adjusting.clear()
            self.Focuser.actGoToPosition(int(position))
            self.adjusting.set()
        else:
            logging.warning('Focuser has crashed...cannot move to absolute position at this time.')
            return False
        return True
        
    def abort_focus_move(self):
        """
        Description
        -----------
        Stops any focuser movements that may be in progress.

        Returns
        -------
        None.

        """
        if not self.crashed.isSet():
            self.Focuser.actStop()
        else:
            pass
        
    def disconnect(self):
        """
        Description
        -----------
        Disconnects from RoboFocus

        Returns
        -------
        None.

        """
        if not self.crashed.isSet():
            self.Focuser.actCloseComm()
            self.live_connection.clear()
        else:
            pass
        
# Robofocus documentation: http://www.robofocus.com/documents/robofocusins31.pdf
