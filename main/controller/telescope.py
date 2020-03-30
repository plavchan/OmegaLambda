import time
import datetime
import win32com.client

# NEEDS TESTING

class Telescope():
    def __init__(self):
        self.Telescope = win32com.client.Dispatch("ASCOM.SoftwareBisque.Telescope")
        '''
        self.Telescope.DeclinationRate = 0.0
        self.Telescope.RightAscensionRate = 0.0 #This is the offset from the sidereal rate, not the absolute rate
        self.Telescope.SiteLatitude = 38.828
        self.Telescope.SiteLongitude = -77.305
        self.Telescope.SiteElevation = 131 #General estimate for GMU, if we need more specific elevation let me know
        self.Telescope.UTCDate = datetime.datetime.now(datetime.timezone.utc)
        '''
        self.Telescope.SlewSettleTime = 3 #seconds after slew as a buffer, may need adjusting
        
        self.check_connection()

        

    def check_connection(self):
        if self.Telescope.Connected == False:
            try: self.Telescope.Connected = True
            except: print("ERROR: Unable to connect to telescope")
            else:  print("Telescope has successfully connected")
        else: print("Telescope is already connected")
        
    def park(self):
        try:
            self.Telescope.Tracking == False
            self.Telescope.Park()
        except: print("ERROR: Error parking telescope or disabling tracking")
        else: print("Telescope is parked; tracking is off")
        
    def unpark(self):
        try: 
            self.Telescope.Unpark()
            self.Telescope.Tracking == True
        except: print("ERROR: Error unparking telescope or enabling tracking")
        else: print("Telescope is unparked; tracking at sidereal rate")

    
    def telescopeSlew(self, ra, dec):
        if self.Telescope.Connected == True:
            self.park() #hopefully the slewsettletime properties applies to park and unpark too, so we won't need to add in a bunch of time.sleep(x) operations
            self.unpark()
            try: self.Telescope.SlewToCoordinates(ra, dec)
            except:
                print("ERROR: Error slewing to target")
        else:
            print("not connected")
    
    def Abort(self):
        self.Telescope.AbortSlew()
        
#Don't know what the cordwrap functions were all about in the deprecated telescope file?
        
        
        
        
        
        
        
        
        
        
    
    
    
