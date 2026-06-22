import time
import threading
import logging
import subprocess
import pywintypes
import win32com.client

from .hardware import Hardware
# Import the custom socket wrapper you created
from .skyx_tcpsocketwrapper import TheSkyXSocketWrapper


class Dome(Hardware):
    
    def __init__(self):
        """
        Initializes the dome as a subclass of hardware.

        Returns
        -------
        None.

        """
        self.domedone = 1
        self.live_connection = threading.Event()
        self.live_connection.set()
        self.live_connection_lock = threading.Lock()
        self.isConnected = 0
        self.shutter = None
        self.atPark = None
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
        self.isConnected = self.Dome.send_js("var res = sky6Dome.isConnected; res;\n")
        print ("self.isConnected in check_connection: ",self.isConnected)
        if self.isConnected:
            self.live_connection.set()
        else:
            self.live_connection.clear()

    def _class_connect(self):
        """
        Connects to your custom socket wrapper and signals the physical mount connect command.

        Returns
        -------
        bool
            True if connection to TheSkyX TCP engine is verified, False otherwise.
        """
        try:
            # Instantiate your socket wrapper class
            self.Dome = TheSkyXSocketWrapper()
            time.sleep(5)
            # Connect the dome hardware if not already connected
            self.Dome.send_js("sky6Dome.Connect();")
            time.sleep(5)      
            self.check_connection()
        except Exception as e:
            logging.error(f"Dome connection failed: {e}")
            return False 
        self.live_connection.is_set()
        return True

    def _is_ready(self,movetype):
        """
        Description
        -----------
        Checks to see if the dome is ready to receive a new command, else
        it waits.
        domemove = 0
        home = 1
        park = 2
        open = 3
        close = 4
        unpark = 5

        Returns
        -------
        None.

        """
        """
        Blocking loop that holds execution until the dome completes its current action.
        """
        self.live_connection.clear()
        self.domedone=0
        with self.move_done_lock:
            while not self.domedone:
                # returns 0 if still moving, 1 if done
                print("Move type: ",movetype)
                match movetype:
                    case 0: # dome move
                        self.domedone = self.Dome.send_js("var res = sky6Dome.IsGoToComplete; res;")
                    case 1: # dome home
                        self.domedone = self.Dome.send_js("var res = sky6Dome.IsFindHomeComplete; res;")
                    case 2: # dome park
                        self.domedone = self.Dome.send_js("var res = sky6Dome.IsParkComplete; res;")
                    case 3: # dome open
                         self.domedone = self.Dome.send_js("var res = sky6Dome.IsOpenComplete; res;")
                    case 4: # dome close
                       self.domedone = self.Dome.send_js("var res = sky6Dome.IsCloseComplete; res;")
                    case 5: # dome unpark
                        self.domedone = self.Dome.send_js("var res = sky6Dome.IsUnParkComplete; res;")
                    case _: # bad movetype
                        self.domedone = 1
                try:
                    self.domedone = int(self.domedone)
                except:
                    self.domedone = 1
                print("self.domedone: ",self.domedone)
                time.sleep(5)
            self.live_connection.set()
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
        # Shutter status: 0 = slitstateunknown, 1 = pseudoopen, 2 = pseudoclosed, 3 = open, 4 = closed.
        print("Checking slit state")
        self.live_connection.clear()
        self.domedone=0
        with self.move_done_lock:
            self.shutter = self.Dome.send_js("var res = sky6Dome.slitState; res;")
            print("Checking slit state  r")
        self.live_connection.set()
        self.domedone=1
        print("self.shutter now: ",self.shutter)
    
    def home(self):
        """
        Description
        -----------
        Homes the dome.

        Returns
        -------
        None.

        """
        if self.Dome.AtHome:
            logging.info("Dome is already at home")
            self.move_done.set()
        else:
            self.move_done.clear()
            with self.move_done_lock:
                val = self.Dome.send_js("var res = sky6Dome.FindHome(); res;")
                logging.info("Dome is homing")
                self._is_ready(1)
            self.move_done.set()
        return
    
    def park(self):
        """
        Description
        -----------
        Parks the dome.
        """
        
        if self.AtPark:
            logging.info("Dome is already at park")
        else:
            self.move_done.clear()
            with self.move_done_lock:
                val = self.Dome.send_js("var res = sky6Dome.Park(); res;")
                logging.info("Dome is parking")
                self._is_ready(2)
                self.AtPark = True
            self.move_done.set()
        return
        
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
        self.live_connection.clear()
        if open_or_close == 'open':
            with self.move_done_lock:
                val = self.Dome.send_js("var res = sky6Dome.OpenSlit(); res;")
                logging.info("Shutter is opening")
                self._is_ready(3)
                time.sleep(2)
        elif open_or_close == 'close':
            with self.move_done_lock:
                val = self.Dome.send_js("var res = sky6Dome.CloseSlit(); res;")
                logging.info("Shutter is closing")
                self._is_ready(4)
                time.sleep(2)
        else:
            logging.critical("Invalid shutter move command")
        self.shutter_position()
        print("Shutter position after",open_or_close,":",self.shutter)
        return
    
    def sync_dome_to_scope(self, toggle):
        """
        Parameters
        ----------
        toggle : BOOL
            If True, will sync the dome movements to the telescope movement.
            If False, will stop syncing the dome movements to the telescope movement.

        Returns
        -------
        None.
        """
        self.move_done.clear()
        if toggle is True:
            with self.move_done_lock:
                val = self.Dome.send_js("var res = sky6Dome.setIsCoupledToMountTracking(1); res;")
                logging.info("Dome is syncing to scope")
                self._is_ready(0)
                time.sleep(5)
                self.move_done.set()
        elif toggle is False:
            with self.move_done_lock:
                val = self.Dome.send_js("var res = sky6Dome.setIsCoupledToMountTracking(0); res;")
                logging.info("Dome is not syncing to scope")
                self._is_ready(0)
                time.sleep(5) 
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
        with self.move_done_lock:
            cmd = f'var res = skyDome6.GoToAzEl({azimuth},0); res;\n'
            val = self.Dome.send_js(cmd)
            logging.info("Dome is slewing to {} degrees".format(azimuth))
            self._is_ready(0)
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
        self.move_done.clear()
        with self.move_done_lock:
            val = self.Dome.send_js("var res = sky6Dome.Abort(); res;")
            logging.info("Dome is aborting")
            self._is_ready(0)
            self.move_done.set()
            return True
        
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

        self.move_shutter('close')
        self.park()

        if self.AtPark and self.Dome.shutter_position() == 4:
            with self.move_done_lock:
                logging.info("Dome is closed and parked, disconnecting...")   
                val = self.Dome.send_js("var res = sky6Dome.Disconnect(); res;")
                time.sleep(2)
                if self.isConnected == False:
                    logging.info("Dome is disconnected.")   
                else:
                    logging.critical("Dome is not disconnected")
        else: 
            logging.critical("Dome is not parked, or shutter not closed")
        