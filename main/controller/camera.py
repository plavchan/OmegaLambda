import time
import threading
import logging

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
        self.exposing = threading.Lock()
        super(Camera, self).__init__(name='Camera')
        
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
        try:
            self.Camera.CoolerOn = True
        except:
            logging.error("Could not turn on cooler")
        
        if self.Camera.CoolerOn and toggle is True:
            try:
                self.Camera.TemperatureSetpoint = self.config_dict.cooler_setpoint
            except:
                logging.warning('Could not change camera cooler setpoint')
            else:
                print("Cooler Setpoint set to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
        elif toggle is False:
            try:
                self.Camera.TemperatureSetpoint = self.config_dict.cooler_idle_setpoint
            except:
                logging.warning('Could not change camera cooler setpoint')
            else:
                print("Cooler Setpoint set to {0:.1f} C".format(self.Camera.TemperatureSetpoint))

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
        if not self.Camera.CoolerOn:
            self.cooler_set(True)
        
        t_diff = abs(self.Camera.TemperatureSetpoint - self.Camera.Temperature)
        power = self.Camera.CoolerPower
    
        if t_diff >= 0.1 and power >= 99:
            if t_diff >= 10:
                self.Camera.TemperatureSetpoint += 5
            elif t_diff >= 5:
                self.Camera.TemperatureSetpoint += 3
            else:
                self.Camera.TemperatureSetpoint += 1
            print("Cooler Setpoint adjusted to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
        elif t_diff <= 0.1 and power <= 40:
            self.Camera.TemperatureSetpoint -= 1
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
        while not (self.Camera.TemperatureSetpoint - 0.1 <= self.Camera.Temperature <= self.Camera.TemperatureSetpoint
                   + 0.1):
            if t >= self.config_dict.cooler_settle_time:
                self._cooler_adjust()
            print("Waiting for cooler to settle...")
            time.sleep(60)
            t += 1
        time.sleep(1)
        print("Cooler has settled")
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

    def expose(self, exposure_time, _filter, save_path=None, _type="light"):
        """
        Parameters
        ----------
        exposure_time : INT
            Exposure time of the image in seconds.
        _filter : INT
            Which filter to expose in.
        save_path : STR, optional
            File path to where the image should be saved. The default is None, which will not
            save the image.
        _type : STR, INT optional
            Image type to be taken. Posssible ARGS:
            "light", "dark", 1, 0. The default is "light".

        Returns
        -------
        None.
        """
        while self.crashed.isSet():
            time.sleep(1)
        with self.exposing:
            if _type == "light":
                _type = 1
            elif _type == "dark":
                _type = 0
            else:
                print("ERROR: Invalid exposure type.")
                return
            logging.debug('Exposing image')
            self.Camera.SetFullFrame()
            self.Camera.Expose(exposure_time, _type, _filter)
            check = self._image_ready()
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
            except:
                logging.error("Could not disconnect from camera")
            else:
                print("Camera has successfully disconnected")
        else:
            print("Camera is already disconnected")

    def set_gain(self):
        pass

    def set_binning(self, factor):
        pass
