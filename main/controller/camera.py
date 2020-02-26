import time

import win32com.client


# NEEDS TESTING

class Camera():
    def __init__(self):
        self.Camera = win32com.client.Dispatch("MaxIM.CCDCamera")  # Sets the camera connection path to the CCDCamera
        self.Camera.DisableAutoShutdown = True  # All of these settings are just basic camera setup settings.
        #self.Camera.LockApp = True
        self.Camera.AutoDownload = True

        self.check_connection()
    
    T_0 = -30

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

    def expose(self, exposure_time, filter, save_path, type="light"):
        if type == "light": #probably will have to change this, 1 translated to the UV filter
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

    def set_binning(self):
        pass

#test