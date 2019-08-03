import os
import time
import win32com.client
import logging


# NEEDS TESTING


class Camera:
    def __init__(self, output_directory):
        # __all__ = ['__init__', 'Camera']  # for some reason, opens up the class and __init__ file?
        # output_directory starts from user path
        self.logger = logging.getLogger(__name__)
        self.output_directory = output_directory
        self.camera = win32com.client.Dispatch("MaxIm.CCDCamera")  # Sets the camera connection path to the CCDCamera
        try:
            self.camera.LinkEnabled = True
            self.logger.info("Camera is connected : "+__name__)
        except:
            self.logger.critical("Camera is not connected : "+__name__)
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
        while self.camera.ImageReady == False:
            time.sleep(1)
            if self.camera.ImageReady:
                # self.camera.StartDownload
                path = os.path.expanduser('~')
                self.camera.SaveImage(os.path.join(path, 'Desktop', "test_pictures.fit"))

    def log(self):
        self.logger.info("Camera test " + __name__)
        if self.camera.LinkEnabled:
            self.logger.info("Camera is connected : "+__name__)
        elif not self.camera.LinkEnabled:
            self.logger.critical("Camera cannot connect : "+__name__)

    def set_gain(self):
        pass

    def set_binning(self):
        pass
