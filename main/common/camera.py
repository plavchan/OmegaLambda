import os
import time
import win32com.client

# NEEDS TESTING

class Camera():
    def __init__(self, output_directory):
        # output_directory starts from user path
        self.output_directory = output_directory
        self.Camera = win32com.client.Dispatch("MaxIm.CCDCamera")  # Sets the camera connection path to the CCDCamera
        self.Camera.DisableAutoShutdown == True  # All of these settings are just basic camera setup settings.
        self.Camera.LockApp == True
        self.Camera.CoolerOn == True
        self.Camera.AutoDownload == True

        try:
            self.Camera.LinkEnabled == True
            print("Camera is connected")

        except:
            print("Camera is not Connected")
            return

    def expose(self, exposure_time, filter, type="light"):
        if type == "light":
            type = 1
        elif type == "dark":
            type = 0
        self.Camera.SetFullFrame()
        self.Camera.Expose(exposure_time, type, filter)
        while Camera.ImageReady==False:
            time.sleep(1)
            if Camera.ImageReady:
                Camera.StartDownload
                path = os.path.expanduser(self.output_directory)
                Camera.SaveImage(os.path.join(path, "test_pictures.fit"))

    def set_gain(self):
        pass

    def set_binning(self):
        pass

    def log(self):
        return self.camera.CameraState
        a="Camera is Idle: Able to start exposures"
        b="Camera is Waiting: Exposure has started"
        c="Camera is Exposing: Exposure is currently in process"
        d="Camera is Reading: Camera array is being read out"
        e="Camera is Downloading: Downloading data to PC"
        f="CAMERA ERROR!!!"
        if self.camera.CameraState == 0:
            return a
        elif self.camera.CameraState == 1:
            return b
        elif self.camera.CameraState == 2:
            return c
        elif self.camera.CameraState == 3:
            return d
        elif self.camera.CameraState == 4:
            return e
        elif self.camera.CameraState == 5:
            return f
