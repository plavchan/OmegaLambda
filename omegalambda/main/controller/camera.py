import time
import threading
import _thread
import json
import logging
import psutil
import pywintypes
import subprocess
import sys
import win32com.client
import os
from os.path import dirname, join
import signal
from typing import Optional, Union

from .hardware import Hardware


class Timeout:
  def __init__(self, timeout):
    self.timeout = timeout
    self.exited = False

  def __enter__(self):
    threading.Thread(target=self.wait_for_timeout).start()

  def wait_for_timeout(self):
    time.sleep(self.timeout)
    if not self.exited:
        logging.error("Timeout reached, exiting thread.")
        _thread.interrupt_main()

  def __exit__(self, a, b, c):
       self.exited = True


class Camera(Hardware):
    cam_type = "CCD"
    fov = 26  # Field of view in arcminutes

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
                logging.info("Cooler Setpoint adjusted to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
            elif t_diff <= -0.5:
                self.Camera.TemperatureSetpoint -= 0.5
                logging.info("Cooler Setpoint adjusted to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
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
            logging.info("Waiting for cooler to settle...")
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


class NIRCamera(Camera):
    cam_type = "NIR"
    fov = 10  # Field of view in arcminutes
    proc = None
    current_dir = dirname(__file__)
    exp_done = threading.Event()
    exposure_time_scale = 1.3  # Scale factor for exposure time to account for overhead

    SINGLE_EXPOSURE_SIG = signal.SIGSEGV
    RESUME_SIG = signal.SIGILL
    PAUSE_SIG = signal.SIGFPE

    """Implement the methods from the Camera class, but most of them won't do anything."""

    def check_connection(self):
        self.live_connection.set()
        return

    def _class_connect(self):
        self.check_connection()
        return True

    def cooler_set(self, toggle):
        self.cooler_status = toggle
        return

    def _cooler_adjust(self):
        return

    def cooler_ready(self):
        self.cooler_settle.set()
        return

    def _image_ready(self):
        return True

    def get_fwhm(self):
        self.fwhm = None

    def expose(self, exposure_time, filter, save_path=None, type="light", **header_kwargs):
        return

    def _write_capture_code_config(self, config):
        with open(join(self.current_dir, "cred2", "cred2_capture_config.json"), "w") as f:
            json.dump(config, f, indent=4)
        logging.info("CRED2 capture code configuration file written.")

    def _run_capture_code(self, cmd_args=[]):
        if self.proc is not None:
            logging.info("Terminating previous CRED2 capture code process...")
            self.disconnect()
        self.proc = subprocess.Popen(
            [sys.executable, "-u", join(self.current_dir, "cred2", "cred2_capture.py"), *cmd_args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            # creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        logging.info("NIR Camera connected. CRED2 capture code process started.")
    
    def _wait_for_capture_end(self):
        if self.proc is None:
            logging.error("No CRED2 capture code process running.")
            return

        for line in self.proc.stdout:
            if "DONE TAKING" in line:
                logging.info("Received end of capture message.")
                return True

        logging.error("Did not receive expected end of capture message.")
        return False

    def start_exposing(self, exposure_time, save_dir, name, calibration=None, num_exposures=None, wait_for_cooler=True):
        """
        Starts continuously exposing images using the NIR camera. Runs the capture code in a separate process.
        Pass 'flats' or 'darks' to the calibration parameter to take calibration images.
        """
        self.exp_done.clear()

        if num_exposures == 1 and self.proc is not None:
            self.send_signal(self.SINGLE_EXPOSURE_SIG)  # take one exposure
            time.sleep(exposure_time + 5)
            self.exp_done.set()
            return

        config = {
            "total_run_time_seconds": 0.0,  # Continuous
            "image_stack_time_seconds": float(exposure_time),
            "data_directory": save_dir,
            "filename_prefix": name + "-",
            "wait_for_cooler_settle": wait_for_cooler,
            "startup_only": num_exposures == 1
        }

        if num_exposures and num_exposures > 1:
            config["total_run_time_seconds"] = float(num_exposures) * float(exposure_time)

        self._write_capture_code_config(config)

        if calibration:
            self._run_capture_code(cmd_args=[calibration])
            time.sleep(10)
            self.disconnect(timeout=5 * 60, terminate=False)          
        else:
            self._run_capture_code()

        if num_exposures:
            if num_exposures == 1:
                self.send_signal(self.SINGLE_EXPOSURE_SIG)  # take one exposure
                # time.sleep(self.exposure_time_scale * exposure_time + 120)
                with Timeout(self.exposure_time_scale * exposure_time + min(3 * exposure_time, 30)):
                    self._wait_for_capture_end()
                self.exp_done.set()
                return
            
            # time.sleep(self.exposure_time_scale * config["total_run_time_seconds"] + 120)
            with Timeout(self.exposure_time_scale * config["total_run_time_seconds"] + min(3 * exposure_time, 30)):
                self._wait_for_capture_end()
            self.disconnect(timeout=exposure_time, terminate=False)
            self.exp_done.set()

    def pause_exposing(self):
        if self.proc is not None:
            self.send_signal(self.PAUSE_SIG)
            logging.info("NIR camera captures paused.")
        else:
            logging.warning("NIR camera is not connected. Cannot pause.")

    def resume_exposing(self):
        if self.proc is not None:
            self.send_signal(self.RESUME_SIG)
            logging.info("NIR camera captures resumed.")
        else:
            logging.warning("NIR camera is not connected. Cannot resume.")

    def disconnect(self, timeout=15, terminate=True):
        """
        Description
        ----------
        Disconnects the camera

        Returns
        -------
        None.
        """
        if self.proc is not None:
            try:
                if terminate:
                    self.proc.send_signal(signal.CTRL_C_EVENT)
                self.proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if not terminate:
                    self.disconnect(terminate=True)
                    return

                logging.warning("CRED2 capture code process did not terminate in time. Terminating subprocess.")
                try:
                    self.proc.terminate()
                    self.proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    logging.warning("CRED2 capture code process still did not terminate.")
                    # logging.warning("CRED2 capture code process did not terminate in time. Terminating process group.")
                    # os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
                    # time.sleep(60)
                    # if psutil.pid_exists(self.proc.pid):
                    #     logging.error("Process group still not terminated. Sending SIGKILL.")
                    #     os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
            finally:
                self.proc = None
            logging.info("NIR Camera has been disconnected")
        else:
            logging.info("NIR Camera is already disconnected")

    def send_signal(self, sig):
        if not self.proc:
            return
        # Copied over from the Linux subprocess.Popen.send_signal
        self.proc.poll()
        if self.proc.returncode is not None:
            return
        try:
            os.kill(self.proc.pid, sig)
        except ProcessLookupError:
            pass

    def set_gain(self):
        pass

    def set_binning(self, factor):
        pass
