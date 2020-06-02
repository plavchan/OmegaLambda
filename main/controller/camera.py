import time
import win32com.client
from main.common.IO import config_reader
import threading

class Camera(threading.Thread):
    
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = True
        
        self.Camera = win32com.client.Dispatch("MaxIm.CCDCamera") #Sets the camera connection path to the CCDCamera
        self.check_connection()
        self.Application = win32com.client.Dispatch("MaxIm.Application")
        self.Camera.DisableAutoShutdown = True  # All of these settings are just basic camera setup settings.
        self.Application.LockApp = True
        self.Camera.AutoDownload = True
        self.config_dict = config_reader.get_config()
        
        self.coolerSet()
        
    def run(self):
        while self.running:
            print("Camera thread is alive")
            time.sleep(5)
            
    def stop(self):
        self.running = False

    def check_connection(self):
        if self.Camera.LinkEnabled:
            print("Camera is already connected")
        else:
            try: 
                self.Camera.LinkEnabled = True
            except: print("ERROR: Could not connect to camera")
            else: print("Camera has successfully connected") 
        
    def coolerSet(self, temp=None):
        try: self.Camera.CoolerOn = True
        except: print("ERROR: Could not turn on cooler")
        
        if self.Camera.CoolerOn and temp == None:
            try: self.Camera.TemperatureSetpoint = self.config_dict.cooler_setpoint
            except: pass
            else: print("Cooler Setpoint set to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
        elif temp != None:
            try: self.Camera.TemperatureSetpoint = temp
            except: pass
            else: print("Cooler Setpoint set to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
        
    def coolerAdjust(self):
        if not self.Camera.CoolerOn:
            self.coolerSet()
        
        if not self.Camera.ImageReady:
            print("Camera is currently exposing--cooler setpoint not changed.")
            
        else:
            T_diff = abs(self.Camera.TemperatureSetpoint - self.Camera.Temperature)
            Power = self.Camera.CoolerPower
        
            if T_diff >= 1 and Power >= 99:
                self.Camera.TemperatureSetpoint += 5
                print("Cooler Setpoint adjusted to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
            
            elif T_diff <= 0.1 and Power <= 40:
                self.Camera.TemperatureSetpoint -= 5
                print("Cooler Setpoint adjusted to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
    
    def cooler_ready(self):
        while not (self.Camera.TemperatureSetpoint - 0.1 <= self.Camera.Temperature <= self.Camera.TemperatureSetpoint + 0.1):
            time.sleep(1)
        else:
            return
    
    def image_ready(self):
        while not self.Camera.ImageReady:
            time.sleep(1)
        if self.Camera.ImageReady:
            return

    def expose(self, exposure_time, filter, save_path=None, type="light"):
        if type == "light":
            type = 1
        elif type == "dark":
            type = 0
        else:
            print("ERROR: Invalid exposure type.")
            return
        self.cooler_ready()
        self.Camera.SetFullFrame()
        self.Camera.Expose(exposure_time, type, filter)
        self.image_ready()
        if save_path == None:
            return
        else:
            self.Camera.SaveImage(save_path)
                
    def disconnect(self):
        if self.Camera.LinkEnabled:
            self.image_ready()
            try: 
                self.coolerSet(self.config_dict.cooler_idle_setpoint)
                self.Camera.Quit()
            except: print("ERROR: Could not disconnect from camera")
            else: print("Camera has successfully disconnected")
        else: print("Camera is already disconnected")
                
    def set_gain(self):
        pass

    def set_binning(self, factor):
        pass
        