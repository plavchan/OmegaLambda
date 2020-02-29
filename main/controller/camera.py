import time

import win32com.client


# NEEDS TESTING

class Camera():
    def __init__(self):
        self.Camera = win32com.client.Dispatch("MaxIM.CCDCamera")  # Sets the camera connection path to the CCDCamera
        self.Application = win32com.client.Dispatch("MaxIm.Application")
        self.Document = win32com.client.Dispatch("MaxIm.Document")
        self.Camera.DisableAutoShutdown = True  # All of these settings are just basic camera setup settings.
        self.Application.LockApp = True
        self.Camera.AutoDownload = True
        self.coolersetpoint = -30

        self.check_connection()

    def check_connection(self):
        if self.Camera.LinkEnabled == True:
            print("Camera is already connected")
        else:
            try:
                self.Camera.LinkEnabled = True
            except:
                print("Camera cannot connect")
            else:
                print("Camera has successfully connected")
        
    def coolerSet(self):
        try: self.Camera.CoolerOn = True
        except: print("Cooler Error")
        
        if self.Camera.CoolerOn == True:
            try: self.Camera.TemperatureSetpoint = self.coolersetpoint
            except: pass
        
    def coolerAdjust(self):
        if self.Camera.CoolerOn == False:
            self.coolerSet()
        
        T_diff = abs(self.TemperatureSetpoint - self.Temperature)
        Power = self.CoolerPower
        
        if T_diff >= 1 and Power >= 95:
            self.TemperatureSetpoint += 5

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
        while self.Camera.ImageReady==False:
            time.sleep(1)
            if self.Camera.ImageReady:
                self.Camera.StartDownload
                #TODO: Automate image nomenclature 
                self.Camera.SaveImage(save_path)

    def set_gain(self):
        pass

    def set_binning(self, factor):
        if factor == 2 or factor == 3:
            self.Document.Bin(factor)
        else:
            print("ERROR: Invalid binning factor")
        