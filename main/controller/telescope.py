import win32com.client
import time
from main.common.IO import config_reader
from main.common.util import conversion_utils


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
       
    def is_ready(self):
        while self.Telescope.Slewing:
            time.sleep(1)
        if not self.Telescope.Slewing:
            return
          
    def Park(self):
        self.is_ready()
        try: 
            self.Telescope.Tracking = False
            self.Telescope.Park()
                
        except: 
            print("ERROR: Could not park telescope")
            return False
        else: 
            print("Telescope is parked, tracking off")
            return True
        
    def Unpark(self):
        self.is_ready()
        try: 
            self.Telescope.Unpark()
            self.Telescope.Tracking = True
        except: 
            print("ERROR: Error unparking telescope or enabling tracking")
            return False
        else: 
            print("Telescope is unparked; tracking at sidereal rate")
            return True
    
    def Slew(self, ra, dec):
        if self.check_coordinate_limit(ra, dec) == False:
            print("ERROR: Cannot slew below 15 degrees altitude.")
            return False
        else:
            self.is_ready()
            try: 
                self.Telescope.SlewToCoordinates(ra, dec) 
            except:
                print("ERROR: Error slewing to target")
            else:
                return True
    
    def PulseGuide(self, direction, duration):                      #Direction str, duration in SECONDS
        direction_key = {"up": 0, "down": 1, "left": 2, "right": 3}
        
        if direction in direction_key:
            direction_num = direction_key[direction]
        else:
            print("ERROR: Invalid pulse guide direction")
            return False
        
        duration = duration*1000                                    #Convert seconds to milliseconds
        self.is_ready()
        try:
            self.Telescope.PulseGuide(direction_num, duration)
        except:
            print("ERROR: Could not pulse guide")
            return False
        else:
            return True
            
    def Jog(self, direction, distance):
        rates_key = {**dict.fromkeys(["up","down"], self.Telescope.GuideRateDeclination),       #Usually the guide rates are the same
                     **dict.fromkeys(["left","right"], self.Telescope.GuideRateRightAscension)}
        distance_key = {**dict.fromkeys(["up","left"], distance),
                        **dict.fromkeys(["down","right"], -distance)}
        
        if direction in rates_key:
            rate = rates_key[direction]
            distance = distance_key[direction]
        
        if distance < 30*60:                       
            duration = (distance/3600)/rate #should be in seconds
            self.PulseGuide(direction, duration)
            
        elif distance >= 30*60:
            if direction in ("up", "down"):
                self.Slew(self.Telescope.RightAscension, self.Telescope.Declination + distance)
            elif direction in ("left", "right"):
                self.Slew(self.Telescope.RightAscension + distance, self.Telescope.Declination)
    
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
        self.is_ready()
        if self.Telescope.AtPark:
            try: 
                del self.Telescope                                         #Both this and self.Telescope.Quit() didn't work
            except: print("ERROR: Could not disconnect from telescope")
        else: 
            print("Telescope is not parked.  Parking telescope before disconnecting.")
            self.Park()
            self.disconnect()
        
        
#Don't know what the cordwrap functions were all about in the deprecated telescope file?
