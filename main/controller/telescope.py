import win32com.client
import time
from main.common.IO import config_reader
from main.common.util import conversion_utils

# NEEDS TESTING

class Telescope():
    def __init__(self):
        self.Telescope = win32com.client.Dispatch("ASCOM.SoftwareBisque.Telescope")
        self.config_dict = config_reader.get_config()
        self.Telescope.SlewSettleTime = 1
       
        self.check_connection()

        
    def check_connection(self):
        if not self.Telescope.Connected:
            try: 
                self.Telescope.Connected = True
                #self.DriverAccess.Connected = True
            except: print("ERROR: Could not connect to the telescope")
        else: print("Already connected")
        
    def check_coordinate_limit(self, ra, dec, time=None):
       (az, alt) = conversion_utils.convert_RaDec_to_AltAz(ra, dec, self.config_dict.site_latitude,
                                                           self.config_dict.site_longitude, time)
       if alt <= 15:
           return False
       else:
           return True
       #TODO: Figure out if there are any other limits
          
    def Park(self):
        while self.Telescope.Slewing:
            time.sleep(1)
        if not self.Telescope.Slewing:
            try: 
                self.Telescope.Tracking = False
                self.Telescope.Park()
                
            except: print("ERROR: Could not park telescope")
            else: print("Telescope is parked, tracking off")
            
        
    def Unpark(self):
        while self.Telescope.Slewing:
            time.sleep(1)
        if not self.Telescope.Slewing:
            try: 
                self.Telescope.Unpark()
                self.Telescope.Tracking = True
            except: print("ERROR: Error unparking telescope or enabling tracking")
            else: print("Telescope is unparked; tracking at sidereal rate")
    
    def Slew(self, ra, dec):
        if self.check_coordinate_limit(ra, dec) == False:
            return print("ERROR: Cannot slew below 15 degrees altitude.")
        else:
            if self.Telescope.Connected:
                while self.Telescope.Slewing:
                    time.sleep(1)
                if not self.Telescope.Slewing:
                    try: 
                        self.Telescope.SlewToCoordinates(ra, dec) 
                    except:
                        print("ERROR: Error slewing to target")
            else:
                print("ERROR: Telescope not connected")
            
    def Jog(self, direction, distance):                             #Distance in arcseconds
        directions_key = {"up": 0, "down": 1, "left": 2, "right": 3}
        rates_key = {**dict.fromkeys(["up","down"], self.Telescope.GuideRateDeclination),
                     **dict.fromkeys(["left","right"], self.Telescope.GuideRateRightAscension)}
        
        if distance < 30*60:                                        #30 arcminutes
            if direction in directions_key:                        
                direction_num = directions_key[direction]
                rate = rates_key[direction]
            else:
                return print("ERROR: Invalid jog direction")
            
            duration = (distance/3600)/rate #should be in seconds
            try:
                self.Telescope.PulseGuide(direction_num, duration*1000) #duration in milliseconds
            except:
                print("ERROR: Could not jog telescope")
                return False
            else:
                return True
        elif distance >= 30*60:
            print("ERROR: Cannot jog more than 30 arcminutes")
    
    def SlewAltAz(self, az, alt, time=None): #input alt/az in degrees
        if alt <= 15:
            return print("ERROR: Cannot slew below 15 degrees altitude.")
        else:
            (ra, dec) = conversion_utils.convert_AltAz_to_RaDec(az, alt, self.config_dict.site_latitude,
                                                            self.config_dict.site_longitude, time)
            self.Slew(ra, dec)
    
    def Abort(self):
        self.Telescope.AbortSlew()
        
    def disconnect(self):
        if self.Telescope.Connected:
            try: del self.Telescope                                         #Both this and self.Telescope.Quit() didn't work
            except: print("ERROR: Could not disconnect from telescope")
        else: print("Telescope is already disconnected")
        
        
#Don't know what the cordwrap functions were all about in the deprecated telescope file?

'''
self.Telescope.DeclinationRate = 0.0
self.Telescope.RightAscensionRate = 0.0 #This is the offset from the sidereal rate, not the absolute rate
self.Telescope.SiteLatitude = 38.828
self.Telescope.SiteLongitude = -77.305
self.Telescope.SiteElevation = 131 #General estimate for GMU, if we need more specific elevation let me know
self.Telescope.UTCDate = datetime.datetime.now(datetime.timezone.utc)
'''