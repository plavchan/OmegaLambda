import win32com.client
import time
import os
from main.common.IO import config_reader
from main.common.util import conversion_utils
import threading
import queue
import logging

class Telescope(threading.Thread):
    
    def __init__(self, loop_time = 1.0/60):
        self.q = queue.Queue()
        self.timeout = loop_time
        self.running = True
        super(Telescope, self).__init__(name='Scope-Th')
        
        self.config_dict = config_reader.get_config()
        self.slew_done = threading.Event()
        
    def onThread(self, function, *args, **kwargs):
        self.q.put((function, args, kwargs))
        
    def run(self):
        self.Telescope = win32com.client.Dispatch("ASCOM.SoftwareBisque.Telescope")
        self.Telescope.SlewSettleTime = 1
        self.check_connection()
        while self.running:
            logging.debug("Telescope thread is alive")
            try:
                function, args, kwargs = self.q.get(timeout=self.timeout)
                function(*args, **kwargs)
            except queue.Empty:
                time.sleep(1)
    
    def stop(self):
        logging.debug("Stopping telescope thread")
        self.running = False
        
    def check_connection(self):
        if not self.Telescope.Connected:
            try: 
                self.Telescope.Connected = True
            except: print("ERROR: Could not connect to the telescope")
            else: print("Telescope has successfully connected")
        else: print("Already connected")
        
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
            self.Telescope.Tracking = True
        except: 
            print("ERROR: Error unparking telescope or enabling tracking")
            return False
        else: 
            print("Telescope is unparked; tracking at sidereal rate")
            return True
    
    def Slew(self, ra, dec):
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
    
    def SlewAltAz(self, az, alt, time=None): #input alt/az in degrees
        if alt <= 15:
            return print("ERROR: Cannot slew below 15 degrees altitude.")
        else:
            (ra, dec) = conversion_utils.convert_AltAz_to_RaDec(az, alt, self.config_dict.site_latitude,
                                                            self.config_dict.site_longitude, time)
            self.Slew(ra, dec)
    
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
