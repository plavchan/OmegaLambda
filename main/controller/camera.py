import time
import win32com.client

from main.controller.filter_wheel import FilterWheel

# NEEDS TESTING

class Camera():
    def __init__(self):
        self.Camera = win32com.client.Dispatch("MaxIm.CCDCamera")  # Sets the camera connection path to the CCDCamera
        self.Camera.DisableAutoShutdown = True  # All of these settings are just basic camera setup settings.
        self.Camera.LockApp = True
        self.Camera.CoolerOn = True
        self.Camera.AutoDownload = True

        self.check_connection()

    def check_connection(self):
        if self.Camera.LinkEnabled == True:
            print("Camera is connected")
        else:
            print("Camera is not connected")


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
        while Camera.ImageReady==False:
            time.sleep(1)
            if Camera.ImageReady:
                Camera.StartDownload
                Camera.SaveImage(save_path)

    def set_gain(self):
        pass

    def set_binning(self):
        pass