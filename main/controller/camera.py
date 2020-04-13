import time
import win32com.client


class Camera():
    
    def __init__(self):
        self.Camera = win32com.client.Dispatch("MaxIm.CCDCamera")  # Sets the camera connection path to the CCDCamera
        self.Application = win32com.client.Dispatch("MaxIm.Application")
        self.Camera.DisableAutoShutdown = True  # All of these settings are just basic camera setup settings.
        self.Application.LockApp = True
        self.Camera.AutoDownload = True
        self.coolersetpoint = 5 #temporarily changed for testing purposes--should be -30 C normally
        
        self.check_connection()
        self.coolerSet()

    def check_connection(self):
        if self.Camera.LinkEnabled:
            print("Camera is already connected")
        else:
            try: self.Camera.LinkEnabled = True
            except: print("ERROR: Could not connect to camera")
            else: print("Camera has successfully connected")
        
    def coolerSet(self):
        try: self.Camera.CoolerOn = True
        except: print("ERROR: Could not turn on cooler")
        
        if self.Camera.CoolerOn:
            try: self.Camera.TemperatureSetpoint = self.coolersetpoint
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

    def expose(self, exposure_time, filter, save_path, type="light"):
        if type == "light":
            type = 1
        elif type == "dark":
            type = 0
        else:
            print("ERROR: Invalid exposure type.")
            return
        self.Camera.SetFullFrame()
        self.Camera.Expose(exposure_time, type, filter)
        while not self.Camera.ImageReady:
            time.sleep(1)
        if self.Camera.ImageReady:
            self.Camera.SaveImage(save_path)
                
    def set_gain(self):
        pass

    def set_binning(self, factor):
        pass
        