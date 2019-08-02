import os
import time
import win32com.client
import logging
      

# NEEDS TESTING

class Camera:
    def __init__(self, output_directory):
        __all__ = ['__init__', 'Camera']                    #for some reason, opens up the class and __init__ file?
        # output_directory starts from user path
        self.output_directory = output_directory
        self.camera = win32com.client.Dispatch("MaxIm.CCDCamera")  # Sets the camera connection path to the CCDCamera

        try:
            self.camera.LinkEnabled = True
        except:
            self.camera.LinkEnabled==False
        self.camera.DisableAutoShutdown = True  # All of these settings are just basic camera setup settings.
        self.camera.AutoDownload = True

        #logging portion
        self.logger = logging.getLogger(__name__ + 'cAmera')     #uses the name and the 'cAmera' logger in the logger.py file    
        self.logger.info('creating an instance of Camera')       

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

    def log(self):
        self.logger.info("starting camera module logging")    #a test point so I know if data gets through
        if self.camera.LinkEnabled:                           #If camera connects, display variable that containd info log
            a=self.logger.info("Camera has connected")
            return a                                          #puts out an a for logger.py to collect
        elif not self.camera.LinkEnabled:                     #If camera does not connect, display variable that contains a critical error
            a=self.logger.critical("Camera cannot connect")
            return a
        self.logger.info("finished camera module logging")

    def set_gain(self):
        pass

    def set_binning(self):
        pass
