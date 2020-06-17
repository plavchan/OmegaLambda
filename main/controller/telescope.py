import win32com.client
import pythoncom
import time
import os
from main.common.IO import config_reader
from main.common.util import conversion_utils
from main.controller.hardware import Hardware
import threading
import queue
import logging

class Telescope(Hardware):
    
    def __init__(self):
        self.slew_done = threading.Event()
        super(Telescope, self).__init__(name='Telescope')
        
    def check_coordinate_limit(self, ra, dec, time=None):
       (az, alt) = conversion_utils.convert_RaDec_to_AltAz(ra, dec, self.config_dict.site_latitude,
                                                           self.config_dict.site_longitude, time)
       if alt <= 15 or dec > 90:
           return False
       else:
           return True
       #TODO: Figure out if there are any other limits
       
    def _is_ready(self):
        while self.Telescope.Slewing:
            time.sleep(1)
        if not self.Telescope.Slewing:
            return
          
    def Park(self):
        self.slew_done.clear()
        self._is_ready()
        try: 
            self.Telescope.Tracking = False
            self.Telescope.Park()
                
        except: 
            print("ERROR: Could not park telescope")
            return False
        else: 
            print("Telescope is parking, tracking off")
            self._is_ready()
            self.slew_done.set()
            return True
        
    def Unpark(self):
        self._is_ready()
        try: 
            self.Telescope.Unpark()
        except: 
            print("ERROR: Error unparking telescope or enabling tracking")
            return False
        else: 
            print("Telescope is unparked; tracking at sidereal rate")
            return True
    
    def Slew(self, ra, dec, tracking=True):     #default tracking is true
        self.slew_done.clear()
        (ra, dec) = conversion_utils.convert_J2000_to_apparent(ra, dec)
        if self.check_coordinate_limit(ra, dec) == False:
            print("ERROR: Cannot slew below 15 degrees altitude.")
            return False
        else:
            self._is_ready()
            try: 
                logging.debug('Telescope slewing')
                self.Telescope.SlewToCoordinates(ra, dec)
                self.Telescope.Tracking = tracking
            except:
                print("ERROR: Error slewing to target")
            else:
                self._is_ready()
                self.slew_done.set()
                return
    
    def PulseGuide(self, direction, duration):                      #Direction str, duration in SECONDS
        self.slew_done.clear()
        direction_key = {"up": 0, "down": 1, "left": 2, "right": 3}
        
        if direction in direction_key:
            direction_num = direction_key[direction]
        else:
            print("ERROR: Invalid pulse guide direction")
            return False
        
        duration = duration*1000                                    #Convert seconds to milliseconds
        self._is_ready()
        try:
            self.Telescope.PulseGuide(direction_num, duration)
        except:
            print("ERROR: Could not pulse guide")
            return False
        else:
            self._is_ready()
            self.slew_done.set()
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
    
    def SlewAltAz(self, az, alt, time=None, tracking=False): #input alt/az in degrees; default tracking is False
        if alt <= 15:
            return print("ERROR: Cannot slew below 15 degrees altitude.")
        else:
            (ra, dec) = conversion_utils.convert_AltAz_to_RaDec(az, alt, self.config_dict.site_latitude,
                                                            self.config_dict.site_longitude, time)
            self.Slew(ra, dec, tracking)
    
    def Abort(self):
        self.Telescope.AbortSlew()
        
    def disconnect(self):   #always park before disconnecting
        self._is_ready()
        if self.Telescope.AtPark:
            try: 
                del self.Telescope
                #self.Telescope.Connected = False
                #os.system("TASKKILL /F /IM TheSkyX.exe")   #This is the only way it will actually disconnect from TheSkyX so far
                #os.system(r"C:\Program Files (x86)\Software Bisque\TheSkyX Professional Edition\TheSkyX.exe")
            except: print("ERROR: Could not disconnect from telescope")
        else: 
            print("Telescope is not parked.")
            return False
        
        
#Don't know what the cordwrap functions were all about in the deprecated telescope file?
