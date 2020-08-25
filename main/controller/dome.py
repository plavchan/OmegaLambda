import time
import threading
import logging
import subprocess
import pywintypes
import win32com.client

from .hardware import Hardware


class Dome(Hardware):
    
    def __init__(self):
        """
        Initializes the dome as a subclass of hardware.

        Returns
        -------
        None.

        """
        self.move_done = threading.Event()
        self.shutter_done = threading.Event()
        self.dome_move_lock = threading.Lock()
        self.shutter = None
        super(Dome, self).__init__(name='Dome')

    def check_connection(self):
        """
        Description
        -----------
        Overwrites base class.  Checks for dome connection specifically.

        Returns
        -------

        """
        logging.info('Checking connection for the {}'.format(self.label))
        self.live_connection.clear()
        self.Dome.Connected = True
        self.live_connection.set()

    def _class_connect(self):
        """
        Description
        -----------
        Overrides base hardware class (not implemented).
        Dispatches COM connection to dome object and sets necessary parameters.
        Should only ever be called from within the run method.

        Returns
        -------
        BOOL
            True if successful, otherwise False.
        """
        try:
            self.Dome = win32com.client.Dispatch("ASCOMDome.Dome")
            self.check_connection()
        except (AttributeError, pywintypes.com_error):
            logging.error('Could not connect to dome')
            return False
        else:
            print('Dome has successfully connected')
        return True

    def _is_ready(self):
        """
        Description
        -----------
        Checks to see if the dome is ready to receive a new command, else
        it waits.

        Returns
        -------
        None.

        """
        while self.Dome.Slewing:
            time.sleep(2)
        if not self.Dome.Slewing:
            return
        
    def shutter_position(self):
        """
        Description
        -----------
        Checks the current position of the shutter.

        Returns
        -------
        None.

        """
        # Shutter status: 0 = open, 1 = closed, 2 = opening, 3 = closing, 4 = error.
        self.shutter = self.Dome.ShutterStatus
    
    def home(self):
        """
        Description
        -----------
        Homes the dome.

        Returns
        -------
        None.

        """
        self._is_ready()
        try:
            with self.dome_move_lock:
                self.Dome.FindHome()
        except pywintypes.com_error:
            logging.error('Dome cannot find home')
        else: 
            print("Dome is homing")
            while not self.Dome.AtHome:
                time.sleep(2)
            return
    
    def park(self):
        """
        Description
        -----------
        Parks the dome.

        Returns
        -------
        bool
            True if successful, otherwise False.

        """
        self.move_done.clear()
        if self.Dome.AtPark:
            print("Dome is at park")
            self.move_done.set()
            return True
        try:
            with self.dome_move_lock:
                self._is_ready()
                self.Dome.Park()
        except pywintypes.com_error:
            logging.error("Error parking dome")
            return False
        else: 
            print("Dome is parking")
            self._is_ready()
            self.move_done.set()
            return True
        
    def move_shutter(self, open_or_close):
        """
        Parameters
        ----------
        open_or_close : STR
            Wether or not the dome shutter is open or closed,
            can either be 'open' or 'close'.

        Returns
        -------
        None.
        """
        self.shutter_done.clear()
        self._is_ready()
        if open_or_close == 'open':
            with self.dome_move_lock:
                self.Dome.OpenShutter()
                print("Shutter is opening")
                time.sleep(2)
            t = 0
            while self.Dome.ShutterStatus in (1, 2, 4):
                time.sleep(5)
                t += 5
                if t >= 5*60:
                    logging.warning('Shutter is still opening...ASCOM may be incorrectly reporting status.')
                    break
            time.sleep(2)
            if self.Dome.ShutterStatus in (0, 2):
                self.shutter_done.set()
            else:
                logging.error('Dome did not open correctly.  Trying again...')
                self.move_shutter('open')
        elif open_or_close == 'close':
            with self.dome_move_lock:
                self.Dome.CloseShutter()
                print("Shutter is closing")
                time.sleep(2)
            t = 0
            while self.Dome.ShutterStatus in (0, 3, 4):
                time.sleep(5)
                t += 5
                if t >= 5*60:
                    logging.warning('Shutter is still closing...ASCOM may be incorrectly reporting status.')
                    break
            time.sleep(2)
            if self.Dome.ShutterStatus in (1, 3):
                self.shutter_done.set()
            else:
                logging.error('Dome did not close correctly.  Trying again...')
                self.move_shutter('close')
        else:
            print("Invalid shutter move command")
        return
    
    def slave_dome_to_scope(self, toggle):
        """
        Parameters
        ----------
        toggle : BOOL
            If True, will slave the dome movements to the telescope movement.
            If False, will stop slaving the dome movements to the telescope movement.

        Returns
        -------
        None.
        """
        self.move_done.clear()
        self._is_ready()
        if toggle is True:
            try:
                with self.dome_move_lock:
                    self.Dome.Slaved = True
            except pywintypes.com_error:
                logging.error("Cannot sync dome to scope")
            else: 
                print("Dome is syncing to scope")
                self._is_ready()
                self.move_done.set()
        elif toggle is False:
            try:
                self.Dome.Slaved = False
            except pywintypes.com_error:
                logging.error("Cannot stop syncing dome to scope")
            else: 
                print("Dome is no longer syncing to scope")
                self.move_done.set()
        logging.debug('Dome syncing toggled')
        
    def slew(self, azimuth):
        """
        Parameters
        ----------
        azimuth : FLOAT
            Azimiuth of intended dome slew.

        Returns
        -------
        None.
        """
        self.move_done.clear()
        self._is_ready()
        try:
            with self.dome_move_lock:
                self.Dome.SlewtoAzimuth(azimuth)
        except pywintypes.com_error:
            logging.error("Error slewing dome")
        else: 
            print("Dome is slewing to {} degrees".format(azimuth))
            self._is_ready()
            self.move_done.set()
    
    def abort(self):
        """
        Description
        -----------
        Aborts the current dome movement.

        Returns
        -------
        None.

        """
        self.Dome.AbortSlew()
        
    def disconnect(self):   # Always close shutter and park before disconnecting
        """
        Description
        -----------
        Disconnects the dome.

        Returns
        -------
        bool
            If False, dome cannot be connected for some reason, if True,
            Dome has disconnected.

        """
        self._is_ready()
        while self.Dome.ShutterStatus != 1:
            time.sleep(5)
        if self.Dome.AtPark and self.Dome.ShutterStatus == 1:
            try: 
                self.Dome.Connected = False
                self.live_conection.clear()
                return True
            except (AttributeError, pywintypes.com_error):
                logging.error("Could not disconnect from dome")
                subprocess.call('taskkill /f /im ASCOMDome.exe')
                subprocess.Popen(r'"C:\Program Files (x86)\Common Files\ASCOM\Dome\ASCOMDome.exe"')
                return False
        else: 
            print("Dome is not parked, or shutter not closed")
            return False
