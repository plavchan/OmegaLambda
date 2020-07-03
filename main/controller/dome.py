import time
import threading
import logging
import subprocess

from .hardware import Hardware

class Dome(Hardware):
    
    def __init__(self):
        self.move_done = threading.Event()
        self.shutter_done = threading.Event()
        super(Dome, self).__init__(name='Dome')
        
    def _is_ready(self):
        while self.Dome.Slewing:
            time.sleep(2)
        if not self.Dome.Slewing:
            return
        
    def ShutterPosition(self):
        # Shutter status: 0 = open, 1 = closed, 2 = opening, 3 = closing, 4 = error.
        self.shutter = self.Dome.ShutterStatus
    
    def Home(self):
        self._is_ready()
        try: self.Dome.FindHome()
        except: print("ERROR: Dome cannot find home")
        else: 
            print("Dome is homing")
            while not self.Dome.AtHome:
                time.sleep(2)
            return
    
    def Park(self):
        self.move_done.clear()
        if self.Dome.AtPark:
            print("Dome is at park")
            self.move_done.set()
            return True
        self._is_ready()
        try: self.Dome.Park()
        except: 
            print("ERROR: Error parking dome")
            return False
        else: 
            print("Dome is parking")
            self._is_ready()
            self.move_done.set()
            return True
        
    def MoveShutter(self, open_or_close):
        self.shutter_done.clear()
        self._is_ready()
        if open_or_close == 'open':
            self.Dome.OpenShutter()
            print("Shutter is opening")
            time.sleep(2)
            while self.Dome.ShutterStatus in (1,2,4):
                time.sleep(5)
            time.sleep(2)
            if self.Dome.ShutterStatus == 0:
                self.shutter_done.set()
            else:
                logging.error('Dome did not open correctly.')
        elif open_or_close == 'close':
            self.Dome.CloseShutter()
            print("Shutter is closing")
            time.sleep(2)
            while self.Dome.ShutterStatus in (0,3,4):
                time.sleep(5)
            time.sleep(2)
            if self.Dome.ShutterStatus == 1:
                self.shutter_done.set()
            else:
                logging.error('Dome did not close correctly.')
            
        else: print("Invalid shutter move command")
        return
    
    def SlaveDometoScope(self, toggle):
        self.move_done.clear()
        self._is_ready()
        if toggle == True:
            try: self.Dome.Slaved = True
            except: print("ERROR: Cannot sync dome to scope")
            else: 
                print("Dome is syncing to scope")
                self._is_ready()
                self.move_done.set()
        elif toggle == False:
            try: self.Dome.Slaved = False
            except: print("ERROR: Cannot stop syncing dome to scope")
            else: 
                print("Dome is no longer syncing to scope")
                self.move_done.set()
        logging.debug('Dome syncing toggled')
        
    def Slew(self, Azimuth):
        self.move_done.clear()
        self._is_ready()
        try: self.Dome.SlewtoAzimuth(Azimuth)
        except: print("ERROR: Error slewing dome")
        else: 
            print("Dome is slewing to {} degrees".format(Azimuth))
            self._is_ready()
            self.move_done.set()
    
    def Abort(self):
        self.Dome.AbortSlew()
        
    def disconnect(self):   #Always close shutter and park before disconnecting
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
                subprocess.call('taskkill /f /im ASCOMDome.exe')
                subprocess.Popen(r'"C:\Program Files (x86)\Common Files\ASCOM\Dome\ASCOMDome.exe"')
                return False
        else: 
            print("Dome is not parked, or shutter not closed")
            return False