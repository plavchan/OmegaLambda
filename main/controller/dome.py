import win32com.client
import time

# NEEDS TESTING

class Dome():
    def __init__(self):
        self.Dome = win32com.client.Dispatch("ASCOMDome.Dome")

        self.connect()

        
    def connect(self):
        try: self.Dome.Connected = True
        except: print("ERROR: Could not connect to dome")
    
    def Home(self):
        while self.Dome.Slewing:
            time.sleep(2)
        if not self.Dome.Slewing:
            try: self.Dome.FindHome()
            except: print("ERROR: Dome cannot find home")
            else: print("Dome is homing")
    
    def Park(self):
        while self.Dome.Slewing:
            time.sleep(2)
        if not self.Dome.Slewing:
            try: self.Dome.Park()
            except: print("ERROR: Error parking dome")
            else: print("Dome is parking")
        
    def MoveShutter(self, open_or_close=None): #I have made it so passing nothing automatically decides to open/close based on current position
        while self.Dome.Slewing:
            time.sleep(2)
        if not self.Dome.Slewing:
            if open_or_close == None:
                status = self.Dome.ShutterStatus
                if status == 1:                 #from my testing it seems like 1 = closed
                    self.Dome.OpenShutter()
                    print("Shutter is opening")
                elif status == 0:
                    self.Dome.CloseShutter()
                    print("Shutter is closing")
        
            elif open_or_close == 'open':
                self.Dome.OpenShutter()
                print("Shutter is opening")
            elif open_or_close == 'close':
                self.Dome.CloseShutter()
                print("Shutter is closing")
            
            else: print("Invalid shutter move command")
    
    #Should work as a toggle on/off
    def SlaveDometoScope(self):
        while self.Dome.Slewing:
            time.sleep(2)
        if not self.Dome.Slewing:
            if self.Dome.Slaved == False:
                try: self.Dome.Slaved = True
                except: print("ERROR: Cannot slave dome to scope")
                else: print("Dome is slaving to scope")
            elif self.Dome.Slaved == True:
                try: self.Dome.Slaved = False
                except: print("ERROR: Cannot stop slaving dome to scope")
                else: print("Dome is no longer slaving to scope")
        
    def Slew(self, Azimuth):
        while self.Dome.Slewing:
            time.sleep(2)
        if not self.Dome.Slewing:
            try: self.Dome.SlewtoAzimuth(Azimuth)
            except: print("ERROR: Error slewing dome")
            else: print("Dome is slewing to {} degrees".format(Azimuth))
    
    def Abort(self):
        self.Dome.AbortSlew()
        
    #This doesn't work for the telescope for some reason
    def disconnect(self):
        while self.Dome.Slewing:
            time.sleep(2)
        if not self.Dome.Slewing:
            if self.Dome.Connected:
                try: self.Dome.Connected = False
                except: print("ERROR: Could not disconnect from dome")
            else: print("Dome is already disconnected")