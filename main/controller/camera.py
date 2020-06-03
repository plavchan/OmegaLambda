import time
import win32com.client
from main.common.IO import config_reader
import threading
import logging

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
            logging.debug("Camera thread is alive")
            time.sleep(5)
            
    def stop(self):
        logging.debug("Stopping camera thread")
        self.running = False

    def check_connection(self):
        if self.Camera.LinkEnabled:
            print("Camera is already connected")
        else:
            try: 
                self.Camera.LinkEnabled = True
            except: print("ERROR: Could not connect to camera")
            else: print("Camera has successfully connected") 
        
    def coolerSet(self):
        try: self.Camera.CoolerOn = True
        except: print("ERROR: Could not turn on cooler")
        
        if self.Camera.CoolerOn:
            try: self.Camera.TemperatureSetpoint = self.config_dict.cooler_setpoint
            except: pass
            else: print("Cooler Setpoint set to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
        
    def _coolerAdjust(self):
        if not self.Camera.CoolerOn:
            self.coolerSet()
        
        T_diff = abs(self.Camera.TemperatureSetpoint - self.Camera.Temperature)
        Power = self.Camera.CoolerPower
    
        if T_diff >= 0.1 and Power >= 99:
            if T_diff >= 10:
                self.Camera.TemperatureSetpoint += 5
            elif T_diff >= 5:
                self.Camera.TemperatureSetpoint += 3
            else:
                self.Camera.TemperatureSetpoint += 1
            print("Cooler Setpoint adjusted to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
        elif T_diff <= 0.1 and Power <= 40:
            self.Camera.TemperatureSetpoint -= 1
            print("Cooler Setpoint adjusted to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
        else:
            pass
    
    def cooler_ready(self):
        t = 0
        while not (self.Camera.Temperature >= self.Camera.TemperatureSetpoint - 0.1 and
                   self.Camera.Temperature <= self.Camera.TemperatureSetpoint + 0.1):
            if t >= 5:                     #5 minutes and cooler still hasn't settled.  Time may need adjusting
                self._coolerAdjust()
            time.sleep(60)
            t += 1
            print("Waiting for cooler to settle...")
        else:
            return
    
    def _image_ready(self):
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
        self._image_ready()
        if save_path == None:
            return
        else:
            self.Camera.SaveImage(save_path)
                
    def disconnect(self):
        if self.Camera.LinkEnabled:
            self._image_ready()
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
        