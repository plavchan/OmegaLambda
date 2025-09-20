import time
import threading
import logging
import pywintypes
import win32com.client

from hardware import Hardware


class TertiaryMirror(Hardware):

    def __init__(self):
        """
        Initializes the Perseus Instrument Selector as a subclass of Hardware.

        Returns
        -------
        None.

        """
        self.tertiarymirror_movement_lock = threading.Lock()
        self.CAMERA_TO_SWITCH_PORT_NAME = {
            "CCD": (1, "SBIG"),
            "NIR": (3, "CRED2"),
        }
        super(TertiaryMirror, self).__init__(name="TertiaryMirror")

    def check_connection(self):
        """
        Description
        -----------
        Overwrites base class.  Checks for tertiary mirror connection specifically.

        Returns
        -------

        """
        logging.info("Checking connection for the {}".format(self.label))
        self.live_connection.clear()
        if self.TertiaryMirror.Connected:
            logging.info("Tertiary mirror is already connected")
        else:
            self.TertiaryMirror.Connected = True
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
            self.TertiaryMirror = win32com.client.Dispatch("ASCOM.PerseusServer.Switch")
            self.check_connection()
        except (AttributeError, pywintypes.com_error):
            logging.error("Cannot connect to tertiary mirror")
            return False
        logging.info("Tertiary mirror has successfully connected")
        return True

    def select_camera(self, camera_name):
        """
        Description
        ----------
        Selects the camera using the tertiary mirror.
        Supported cameras: CCD, NIR.
        Unsupported cameras/devices - will require manually operating the device: Planetary Cam, Eyepiece.

        Returns
        -------
        None.
        """
        camera_name = camera_name.replace('-', '').upper()
        target_camera = self.CAMERA_TO_SWITCH_PORT_NAME.get(camera_name, (None, camera_name))
        target_port, target_name = target_camera

        with self.tertiarymirror_movement_lock:
            if target_port is not None:  # First, try with the port number, which will be fastest
                self.TertiaryMirror.SetSwitchValue(0, target_port)
                time.sleep(5)
                if target_name in self.TertiaryMirror.GetSwitchName(0).replace('-', '').upper():
                    logging.info(f"The {camera_name} camera has been selected at port {target_port}.")
                    return
                logging.error(
                    f"Did not find the {camera_name} camera at the expected port ({target_port}). Attempting to select using name. The port may have changed."
                )
            else:
                logging.error(f"The {camera_name} camera is unknown to the code. Attempting to select using name.")

            for port in range(1, 5):
                self.TertiaryMirror.SetSwitchValue(0, port)
                time.sleep(5)
                if target_name in self.TertiaryMirror.GetSwitchName(0):
                    logging.info(f"The {camera_name} camera has been selected at port {port}.")
                    return
            logging.critical(f"Could not find the {camera_name} camera at any port. Please check the camera name and Perseus Commander.")

    def disconnect(self):
        """
        Description
        ----------
        Disconnects the tertiary mirror

        Returns
        -------
        None.
        """
        if self.TertiaryMirror.Connected:
            try:
                self.TertiaryMirror.Connected = False
                self.live_connection.clear()
            except (AttributeError, pywintypes.com_error):
                logging.error("Could not disconnect from tertiary mirror")
            else:
                logging.info("Tertiary mirror has successfully disconnected")
        else:
            logging.info("Tertiary mirror is already disconnected")
