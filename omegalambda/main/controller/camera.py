import time
import threading
import logging
import pywintypes
import win32com.client
from typing import Optional, Union

from .hardware import Hardware


class Camera(Hardware):
    
    def __init__(self):
        """
        Initializes the camera as a subclass of Hardware.

        Returns
        -------
        None.

        """
        self.cooler_settle = threading.Event()
        self.image_done = threading.Event()
        self.camera_lock = threading.Lock()
        self.fwhm: Optional[Union[float, int]] = None
        self.cooler_status = False
        super(Camera, self).__init__(name='Camera')

    def check_connection(self):
        """
        Description
        -----------
        Overwrites base class.  Checks for camera connection specifically.

        Returns
        -------

        """
        logging.info('Checking connection for the {}'.format(self.label))
        self.live_connection.clear()
        if self.Camera.LinkEnabled:
            logging.info("Camera is already connected")
        else:
            self.Camera.LinkEnabled = True
            self.live_connection.set()

    def _class_connect(self):
        """
        Description
        -----------
        Overrides base hardware class (not implemented).
        Dispatches COM connection to camera object and sets necessary parameters.
        Should only ever be called from within the run method.

        Returns
        -------
        BOOL
            True if successful, otherwise False.
        """
        try:
            self.Camera = win32com.client.Dispatch("MaxIm.CCDCamera")
            self.Application = win32com.client.Dispatch("MaxIm.Application")
            self.check_connection()
        except (AttributeError, pywintypes.com_error):
            logging.error('Cannot connect to camera')
            return False
        else:
            logging.info('Camera has successfully connected')
        # Setting basic configurations for the camera
        self.Camera.DisableAutoShutdown = True
        self.Camera.AutoDownload = True
        self.Application.LockApp = True
        # Starts the camera's cooler--method defined in camera.py
        self.cooler_set(True)
        return True

    def cooler_set(self, toggle):
        """

        Parameters
        ----------
        toggle : BOOL
            If True, will activate camera cooler, if False, will
            set camera cooler temperature to idle temp.

        Returns
        -------
        None.

        """
        with self.camera_lock:
            try:
                self.Camera.CoolerOn = True
            except (AttributeError, pywintypes.com_error):
                logging.error("Could not turn on cooler")

            if self.Camera.CoolerOn and toggle is True:
                try:
                    self.Camera.TemperatureSetpoint = self.config_dict.cooler_setpoint
                    self.cooler_status = True
                except (AttributeError, pywintypes.com_error):
                    logging.warning('Could not change camera cooler setpoint')
                else:
                    logging.info("Cooler Setpoint set to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
            elif toggle is False:
                try:
                    self.Camera.TemperatureSetpoint = self.config_dict.cooler_idle_setpoint
                    self.cooler_status = False
                except (AttributeError, pywintypes.com_error):
                    logging.warning('Could not change camera cooler setpoint')
                else:
                    logging.info("Cooler Setpoint set to {0:.1f} C".format(self.Camera.TemperatureSetpoint))

    def _cooler_adjust(self):
        """
        Description
        -----------
        Checks cooler power and current temp, and adjusts the setpoint
        if the power is at 100% and the temperature is significantly different
        from the setpoint.

        Returns
        -------
        None.

        """
        with self.camera_lock:
            if not self.Camera.CoolerOn:
                self.cooler_set(True)

            t_diff = self.Camera.Temperature - self.Camera.TemperatureSetpoint
            # power = self.Camera.CoolerPower

            if t_diff >= 0.1:
                if t_diff >= 10:
                    self.Camera.TemperatureSetpoint += 5
                elif t_diff >= 5:
                    self.Camera.TemperatureSetpoint += 3
                elif t_diff >= 1:
                    self.Camera.TemperatureSetpoint += 1
                else:
                    self.Camera.TemperatureSetpoint += 0.5
                print("Cooler Setpoint adjusted to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
            elif t_diff <= -0.5:
                self.Camera.TemperatureSetpoint -= 0.5
                print("Cooler Setpoint adjusted to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
            else:
                pass
    
    def cooler_ready(self):
        """
        Description
        -----------
        Waits for x minutes (set in config file) and then starts adjust the cooler setpoint
        every minute until they reach equilibrium.

        Returns
        -------
        None.

        """
        self.cooler_settle.clear()
        t = 0
        last_temp = 0
        while not (self.Camera.TemperatureSetpoint - 0.2 <= self.Camera.Temperature <= self.Camera.TemperatureSetpoint
                   + 0.2):
            print("Waiting for cooler to settle...")
            time.sleep(60)
            t += 1
            if t < self.config_dict.cooler_settle_time:
                continue
            temp = self.Camera.Temperature
            temp_rate = abs(temp - last_temp)
            if temp_rate <= 0.5:
                self.Camera.TemperatureSetPoint = self.Camera.Temperature
                logging.info("Cooler Setpoint adjusted to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
                break
            elif temp_rate <= 3:
                self._cooler_adjust()
            if self.Camera.Temperature < self.Camera.TemperatureSetpoint:
                break
            last_temp = temp
        time.sleep(1)
        logging.info("Cooler has settled")
        self.cooler_settle.set()
        return
    
    def _image_ready(self):
        """
        Description
        -----------
        Checks to see if the previous image is ready for downloading.

        Returns
        -------
        None.
        """
        while self.Camera.ImageReady is False and self.crashed.isSet() is False:
            time.sleep(1)
        if self.Camera.ImageReady:
            return True
        elif self.crashed.isSet():
            self.disconnect()
            return False

    def get_fwhm(self):
        """
        Description
        -----------
        Sets the self.fwhm property to the FLOAT value that is the fwhm of the brightest star in
        the newest CCD exposure.  [Cannot return due to multithreading].

        Returns
        -------
        None.
        """
        self.fwhm = self.Camera.fwhm

    def expose(self, exposure_time, filter, save_path=None, type="light", **header_kwargs):
        """
        Parameters
        ----------
        exposure_time : FLOAT or INT
            Exposure time of the image in seconds.
        filter : INT
            Which filter to expose in.
        save_path : STR, optional
            File path to where the image should be saved. The default is None, which will not
            save the image.
        type : STR, INT optional
            Image type to be taken. Posssible ARGS:
            "light", "dark", 1, 0. The default is "light".

        Returns
        -------
        None.
        """
        while self.crashed.isSet():
            time.sleep(1)
        with self.camera_lock:
            type = 1 if type == "light" else 0 if type == "dark" else None
            if type is None:
                logging.error("Invalid exposure type.")
                return
            logging.debug('Exposing image')
            self.Camera.SetFullFrame()
            self.Camera.Expose(exposure_time, type, filter)
            check = self._image_ready()
            if header_kwargs:
                for key, value in header_kwargs.items():
                    self.Camera.SetFITSKey(key, value)
            if save_path is None:
                return
            elif check:
                self.Camera.SaveImage(save_path)
                self.image_done.set()
                self.image_done.clear()
                
    def disconnect(self):
        """
        Description
        ----------
        Disconnects the camera

        Returns
        -------
        None.
        """
        if self.Camera.LinkEnabled:
            try: 
                self.cooler_set(False)
                self.Camera.Quit()
                self.live_connection.clear()
            except (AttributeError, pywintypes.com_error):
                logging.error("Could not disconnect from camera")
            else:
                logging.info("Camera has successfully disconnected")
        else:
            logging.info("Camera is already disconnected")

    def set_gain(self):
        pass

    def set_binning(self, factor):
        pass
