import win32com.client
import time
import threading
import logging

class Dome(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = True
        
        self.Dome = win32com.client.Dispatch("ASCOMDome.Dome")

        self.connect()
        
    def run(self):
        while self.running:
            logging.debug("Dome thread is alive")
            time.sleep(5)
    
    def stop(self):
        logging.debug("Stopping dome thread")
        self.running = False
        
    def connect(self):
        try: self.Dome.Connected = True
        except: print("ERROR: Could not connect to dome")
        
    def is_ready(self):
        while self.Dome.Slewing:
            time.sleep(2)
        if not self.Dome.Slewing:
            return
    
    def Home(self):
        self.is_ready()
        try: self.Dome.FindHome()
        except: print("ERROR: Dome cannot find home")
        else: print("Dome is homing")
        while not self.Dome.AtHome:
            time.sleep(2)
        return
    
    def Park(self):
        self.is_ready()
        try: self.Dome.Park()
        except: print("ERROR: Error parking dome")
        else: print("Dome is parking")
        
    def MoveShutter(self, open_or_close):
        self.is_ready()
        if open_or_close == 'open':
            self.Dome.OpenShutter()
            print("Shutter is opening")
            while self.Dome.ShutterStatus != 0:
                time.sleep(5)
        elif open_or_close == 'close':
            self.Dome.CloseShutter()
            print("Shutter is closing")
            while self.Dome.ShutterStatus != 1: #Seems like 1 = closed, 0 = open.  Partially opened = open.
                time.sleep(5)
            
        else: print("Invalid shutter move command")
        return
    
    def SlaveDometoScope(self, toggle):
        self.is_ready()
        if toggle == True:
            try: self.Dome.Slaved = True
            except: print("ERROR: Cannot slave dome to scope")
            else: print("Dome is slaving to scope")
        elif toggle == False:
            try: self.Dome.Slaved = False
            except: print("ERROR: Cannot stop slaving dome to scope")
            else: print("Dome is no longer slaving to scope")
        
    def Slew(self, Azimuth):
        self.is_ready()
        try: self.Dome.SlewtoAzimuth(Azimuth)
        except: print("ERROR: Error slewing dome")
        else: print("Dome is slewing to {} degrees".format(Azimuth))
    
    def Abort(self):
        self.Dome.AbortSlew()
        
    def disconnect(self):   #Always close shutter and park before disconnecting
        self.is_ready()
        while self.Dome.ShutterStatus != 1:
            time.sleep(5)
        if self.Dome.AtPark and self.Dome.ShutterStatus == 1:
            try: 
                self.Dome.Connected = False
                return True
            except: 
                print("ERROR: Could not disconnect from dome")
                return False
        else: 
            print("Dome is not parked, or shutter not closed")
            return False