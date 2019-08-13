import os
import time
import win32com.client
import logging

# NEEDS TESTING

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler = logging.FileHandler('C:\\Users\\GMU Observtory1\\Desktop\\CameraErrorLog.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class Camera:

    def __init__(self, output_directory):
        # __all__ = ['__init__', 'Camera']  # for some reason, opens up the class and __init__ file?
        # output_directory starts from user path
        self.output_directory = output_directory
        self.camera = win32com.client.Dispatch("MaxIm.CCDCamera")  # Sets the camera connection path to the CCDCamera
        try:
            self.camera.LinkEnabled = True
            logger.info("Camera is connected")
        except:
            logger.info("Camera is not connected")
        self.camera.DisableAutoShutdown = True  # All of these settings are just basic camera setup settings.
        self.camera.AutoDownload = True

    def expose(self, exposure_time, filter, type="light"):
        if type == "light":
            type = 1
        elif type == "dark":
            type = 0
        else:
            logger.error("Invalid exposure type.")
            return
        self.camera.SetFullFrame()
        self.camera.Expose(exposure_time, type, filter)
        time.sleep(exposure_time)
        while not self.camera.ImageReady:
            logger.info("Exposure is being taken")
            time.sleep(1)
            if self.camera.ImageReady:
                #self.camera.StartDownload
                logger.info("Exposure is downloading")
                path = os.path.expanduser('~')
                self.camera.SaveImage(os.path.join(path, 'Desktop', "test_pictures.fit"))
                logger.info("Exposure has downloaded")

    def set_gain(self):
        pass

    def set_binning(self):
        pass
