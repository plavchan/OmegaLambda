import win32com.client
import pythoncom
import time
import threading
import queue
import logging
from main.controller.hardware import Hardware

class Dome(Hardware):
    
    def __init__(self):
        '''
        

        Returns
        -------
        None.

        '''
        self.move_done = threading.Event()
        self.shutter_done = threading.Event()
        super(Dome, self).__init__(name='Dome')
        
    def _is_ready(self):
        '''
        

        Returns
        -------
        None.

        '''
        while self.Dome.Slewing:
            time.sleep(2)
        if not self.Dome.Slewing:
            return
        
    def ShutterPosition(self):
        '''
        

        Returns
        -------
        None.

        '''
        self.shutter = self.Dome.ShutterStatus
    
    def Home(self):
        '''
        

        Returns
        -------
        None.

        '''
        self._is_ready()
        try: self.Dome.FindHome()
        except: 
            print("ERROR: Dome cannot find home")
            logging.error('Dome cannot find home')
        else: 
            print("Dome is homing")
            logging.debug('Dome is homing')
            while not self.Dome.AtHome:
                time.sleep(2)
            return
    
    def Park(self):
        '''
        

        Returns
        -------
        None.

        '''
        self.move_done.clear()
        self._is_ready()
        try: self.Dome.Park()
        except: 
            print("ERROR: Error parking dome")
            logging.error('Error parking dome')
        else: 
            print("Dome is parking")
            logging.debug('Dome is parking')
            self._is_ready()
            self.move_done.set()
        
    def MoveShutter(self, open_or_close):
        '''
        

        Parameters
        ----------
        open_or_close : STR
            Wether or not the dome shutter is open or closed, 
            can either be 'open' or 'close'.

        Returns
        -------
        None.

        '''
        self.shutter_done.clear()
        self._is_ready()
        if open_or_close == 'open':
            self.Dome.OpenShutter()
            print("Shutter is opening")
            logging.debug('Dome is opening')
            while self.Dome.ShutterStatus != 0:
                time.sleep(5)
            self.shutter_done.set()
        elif open_or_close == 'close':
            self.Dome.CloseShutter()
            print("Shutter is closing")
            logging.debug('Dome is closing')
            while self.Dome.ShutterStatus != 1: #Seems like 1 = closed, 0 = open.  Partially opened/closed = last position.
                time.sleep(5)
            self.shutter_done.set()
            
        else: print("Invalid shutter move command")
            logging.error('Invalid shutter move command')
        return
    
    def SlaveDometoScope(self, toggle):
        '''
        

        Parameters
        ----------
        toggle : BOOL
            If True, will slave the dome movements to the telescope movement.

        Returns
        -------
        None.

        '''
        self.move_done.clear()
        self._is_ready()
        if toggle == True:
            try: self.Dome.Slaved = True
            except: print("ERROR: Cannot slave dome to scope")
                logging.error('Cannot slave dome to scope')
            else: 
                print("Dome is slaving to scope")
                self._is_ready()
                self.move_done.set()
        elif toggle == False:
            try: self.Dome.Slaved = False
            except: print("ERROR: Cannot stop slaving dome to scope")
                logging.error('Cannot stop slaving dome to scope')
            else: print("Dome is no longer slaving to scope")
                logging.debug('Dome no longer slaving to scope')
        logging.debug('Dome slaving toggled')
        
    def Slew(self, Azimuth):
        '''
        

        Parameters
        ----------
        Azimuth : FLOAT
            Azimiuth of intended dome slew.

        Returns
        -------
        None.

        '''
        self.move_done.clear()
        self._is_ready()
        try: self.Dome.SlewtoAzimuth(Azimuth)
        except: print("ERROR: Error slewing dome")
            logging.error('Error slewing dome')
        else: 
            print("Dome is slewing to {} degrees".format(Azimuth))
            logging.debug("Dome is slewing to {} degrees".format(Azimuth))
            self._is_ready()
            self.move_done.set()
    
    def Abort(self):
        '''
        

        Returns
        -------
        None.

        '''
        self.Dome.AbortSlew()
        logging.warning('Dome slew aborted')
        
    def disconnect(self): #Always close shutter and park before disconnecting
        '''
        

        Returns
        -------
        bool
            If False, dome cannot be connected for some reason, if True,
            Dome can be disconnected.

        '''
        self._is_ready()
        while self.Dome.ShutterStatus != 1:
            time.sleep(5)
        if self.Dome.AtPark and self.Dome.ShutterStatus == 1:
            try: 
                self.Dome.Connected = False
                self.live_conection.clear()
                return True
            except: 
                print("ERROR: Could not disconnect from dome")
                logging.error('Could not disconnect from dome')
                return False
        else: 
            print("Dome is not parked, or shutter not closed")
            logging.error('Dome is not parked or the shutter is not closed')
            return False