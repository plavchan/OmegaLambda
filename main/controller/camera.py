import time
import threading
import logging

from .hardware import Hardware

class Camera(Hardware):         # Subclassed from the hardware class
    
    def __init__(self):
        self.cooler_settle = threading.Event()
        self.image_done = threading.Event()
        self.crashed = threading.Event()
        self.exposing = threading.Lock()
        super(Camera, self).__init__(name='Camera')
        
    def coolerSet(self, toggle):
        try: self.Camera.CoolerOn = True
        except: print("ERROR: Could not turn on cooler")
        
        if self.Camera.CoolerOn and toggle == True:
            try: self.Camera.TemperatureSetpoint = self.config_dict.cooler_setpoint
            except: pass
            else: print("Cooler Setpoint set to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
        elif toggle == False:
            try: self.Camera.TemperatureSetpoint = self.config_dict.cooler_idle_setpoint
            except: pass
            else: print("Cooler Setpoint set to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
        
    def _coolerAdjust(self):
        if not self.Camera.CoolerOn:
            self.coolerSet(True)
        
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
        self.cooler_settle.clear()
        t = 0
        while not (self.Camera.Temperature >= self.Camera.TemperatureSetpoint - 0.1 and
                   self.Camera.Temperature <= self.Camera.TemperatureSetpoint + 0.1):
            if t >= self.config_dict.cooler_settle_time:
                self._coolerAdjust()
            print("Waiting for cooler to settle...")
            time.sleep(60)
            t += 1
        time.sleep(1)
        print("Cooler has settled")
        self.cooler_settle.set()
        return
    
    def _image_ready(self):
        while self.Camera.ImageReady == False and self.crashed.isSet() == False:
            time.sleep(1)
        if self.Camera.ImageReady:
            return True
        elif self.crashed.isSet():
            self.disconnect()
            return False

    def expose(self, exposure_time, filter, save_path=None, type="light"):
        with self.exposing:
            if type == "light":
                type = 1
            elif type == "dark":
                type = 0
            else:
                print("ERROR: Invalid exposure type.")
                return
            logging.debug('Exposing image')
            self.Camera.SetFullFrame()
            self.Camera.Expose(exposure_time, type, filter)
            check = self._image_ready()
            if save_path == None:
                return
            elif check:
                self.Camera.SaveImage(save_path)
                self.image_done.set()
                self.image_done.clear()
                
    def get_FWHM(self):
        self.fwhm = self.Camera.FWHM
                
    def disconnect(self):
        if self.Camera.LinkEnabled:
            try: 
                self.coolerSet(False)
                self.Camera.Quit()
                self.live_connection.clear()
            except: print("ERROR: Could not disconnect from camera")
            else: print("Camera has successfully disconnected")
        else: print("Camera is already disconnected")
        
                
    def set_gain(self):
        pass

    def set_binning(self, factor):
        pass
        