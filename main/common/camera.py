import os
import time
import win32com.client


# NEEDS TESTING

class Camera():
    def __init__(self, output_directory):
        # output_directory starts from user path
        self.output_directory = output_directory
        self.camera = win32com.client.Dispatch("MaxIm.CCDCamera")  # Sets the camera connection path to the CCDCamera

        try:
            self.camera.LinkEnabled = True
            print("Camera is connected")

        except:
            print("Camera is not Connected")
            return

        self.camera.DisableAutoShutdown = True  # All of these settings are just basic camera setup settings.
        self.camera.AutoDownload = True

    def expose(self, exposure_time, filter, type="light"):
        if type == "light":
            type = 1
        elif type == "dark":
            type = 0
        else:
            print("ERROR: Invalid exposure type.")
            return
        self.camera.SetFullFrame()
        self.camera.Expose(exposure_time, type, filter)
        time.sleep(exposure_time)
        while self.camera.ImageReady==False:
            time.sleep(1)
            if self.camera.ImageReady:
                self.camera.StartDownload
                path = os.path.expanduser('~')
                self.camera.SaveImage(os.path.join(path, 'Desktop', "test_pictures.fit"))

    def set_gain(self):
        pass

    def set_binning(self):
        pass
