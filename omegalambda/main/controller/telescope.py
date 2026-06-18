import threading
import logging
import time
import subprocess
import os

from ..common.util import conversion_utils, time_utils
from .hardware import Hardware
# Import the custom socket wrapper you created
from .skyx_tcpsocketwrapper import TheSkyXSocketWrapper

class Telescope(Hardware):
    def __init__(self):
        """
        Initializes the telescope subclass inheriting from Hardware.
        """
        super(Telescope, self).__init__("Telescope")
        self.Telescope = None
        self.threads = []
        self.live_connection = threading.Event()
        
    def check_connection(self):
        """
        Verifies communication with TheSkyX via a fast status ping.
        """
        if self.Telescope is None:
            self.live_connection.clear()
            return

        # Query connection status using a quick JS execution echo
        res = self.Telescope.send_js("var res = sky6RASCOMTele.IsConnected; res;")
        if res == "1":
            self.live_connection.set()
        else:
            self.live_connection.clear()

    def _class_connect(self):
        """
        Connects to your custom socket wrapper and signals the physical mount connect command.

        Returns
        -------
        bool
            True if connection to TheSkyX TCP engine is verified, False otherwise.
        """
        try:
            # Instantiate your socket wrapper class
            self.Telescope = TheSkyXSocketWrapper()
            
            # Connect the telescope hardware if not already connected
            self.Telescope.send_js("sky6RASCOMTele.Connect();")
            time.sleep(1)
            
            self.check_connection()
        except Exception as e:
            logging.error(f"Telescope connection failed: {e}")
            return False
        return self.live_connection.is_set()

    def disconnect(self):
        """
        Disconnects the physical telescope mount software-side.

        Returns
        -------
        bool
            True if disconnected successfully.
        """
        self._is_ready()
        if self.Telescope:
            self.Telescope.send_js("sky6RASCOMTele.Disconnect();")
        self.live_connection.clear()
        return True

    def _is_ready(self):
        """
        Blocking loop that holds execution until the telescope completes its current slew.
        """
        while True:
            # IsSlewComplete returns 0 if still moving, 1 if done
            val = self.Telescope.send_js("var res = sky6RASCOMTele.IsSlewComplete; res;")
            if val == "1":
                break
            time.sleep(0.2)

    def park(self):
        """
        Parks the telescope to its resting safety orientation.
        """
        self._is_ready()
        # Turn tracking off natively before parking
        self.Telescope.send_js("sky6RASCOMTele.SetTracking(0, 1, 0.0, 0.0);")
        self.Telescope.send_js("sky6RASCOMTele.Park();")
        self._is_ready()

    def unpark(self):
        """
        Unparks the telescope mount.
        """
        self._is_ready()
        self.Telescope.send_js("sky6RASCOMTele.Unpark();")
        # Explicitly engage default tracking upon unpark
        self.Telescope.send_js("sky6RASCOMTele.SetTracking(1, 1, 0.0, 0.0);")

    def check_current_coords(self):
        """
        Continuously queries the telescope for its current coordinates and
        logs them. This is called as a background thread by the ThreadMonitor.
        """
        coords = self.get_coordinates()
        if coords["ra"] is not None and coords["dec"] is not None:
            # Format to hours/minutes/seconds and degrees/minutes/seconds for logs
            ra_hms = conversion_utils.degrees_to_hms(coords["ra"] * 15.0)  # RA is in hours, convert to degrees first
            dec_dms = conversion_utils.degrees_to_dms(coords["dec"])
            
            logging.debug(f"Current Telescope Coordinates -- RA: {ra_hms[0]}:{ra_hms[1]}:{ra_hms[2]:.2f}, "
                          f"DEC: {dec_dms[0]}:{dec_dms[1]}:{dec_dms[2]:.2f}")
        else:
            logging.warning("ThreadMonitor failed to fetch telescope coordinates.")


    def get_coordinates(self):
        """
        Queries the telescope position and scales them into degrees/hours.

        Returns
        -------
        dict
            A dictionary tracking current 'ra' and 'dec'.
        """
        # Command TheSkyX to grab latest telemetry
        self.Telescope.send_js("sky6RASCOMTele.GetRaDec();")
        
        # Pull values out via separate evaluated expressions
        ra_raw = self.Telescope.send_js("var res = sky6RASCOMTele.dRa; res;")
        dec_raw = self.Telescope.send_js("var res = sky6RASCOMTele.dDec; res;")
        
        try:
            return {
                "ra": float(ra_raw),
                "dec": float(dec_raw)
            }
        except ValueError:
            logging.error("Could not parse coordinates from telescope socket.")
            return {"ra": None, "dec": None}

    def slew(self, ra, dec, tracking=True):
        """
        Asynchronously slews the telescope to target Right Ascension and Declination coordinates.

        Parameters
        -------
        ra : float
            Target Right Ascension in hours.
        dec : float
            Target Declination in degrees.
        tracking : bool, optional
            Whether standard sidereal tracking remains engaged after slew finishes. Default is True.
        """
        if ra < 0 or ra >= 24:
            logging.error(f"Invalid RA coordinate given: {ra}")
            return
        if dec < -90 or dec > 90:
            logging.error(f"Invalid Dec coordinate given: {dec}")
            return

        self._is_ready()
        
        # Native async command sequence mapping to target variables
        cmd = f"sky6RASCOMTele.SlewToRaDecAsync({ra}, {dec}, 'Target Slew');"
        self.Telescope.send_js(cmd)
        
        # Wait until movement is finalized
        self._is_ready()
        
        # Set post-slew tracking state
        track_flag = 1 if tracking else 0
        self.Telescope.send_js(f"sky6RASCOMTele.SetTracking({track_flag}, 1, 0.0, 0.0);")

    def set_tracking(self, tracking=True):
        """
        Toggles telescope target tracking states.
        """
        track_flag = 1 if tracking else 0
        self.Telescope.send_js(f"sky6RASCOMTele.SetTracking({track_flag}, 1, 0.0, 0.0);")

    def set_ra_dec_rates(self, ra_rate, dec_rate):
        """
        Applies custom offset tracking adjustments.

        Parameters
        -------
        ra_rate : float
            Custom right ascension offset tracking rate.
        dec_rate : float
            Custom declination offset tracking rate.
        """
        # SetTracking(bTrackingOn, bTransmitRates, dRaRateOffset, dDecRateOffset)
        cmd = f"sky6RASCOMTele.SetTracking(1, 0, {ra_rate}, {dec_rate});"
        self.Telescope.send_js(cmd)

    def pulse_guide(self, direction, duration):
        """
        Sends low-level pulse adjustments for tracking corrections.

        Parameters
        -------
        direction : str
            Direction value string ('north', 'south', 'east', 'west').
        duration : float
            Pulse length step window in seconds.
        """
        # Convert fractional seconds to milliseconds for native TheSkyX API expectations
        duration_ms = int(duration * 1000)
        
        # Map direction strings to expected object inputs
        dir_map = {
            "north": "dNorth",
            "south": "dSouth",
            "east": "dEast",
            "west": "dWest"
        }
        
        target_dir = dir_map.get(direction.lower())
        if not target_dir:
            logging.error(f"Unknown pulse guide direction: {direction}")
            return
            
        cmd = f"sky6RASCOMTele.PulseGuide({duration_ms}, {target_dir});"
        self.Telescope.send_js(cmd)

    def jog(self, direction, distance):
        """
        Jogs the telescope position using small fixed step increments.
        """
        # Retained logic interface utilizing pulse guide timing blocks to approximate step movement distances safely
        # Note: If your system configuration relies on guide rate values, adjust math ratios accordingly
        duration = distance / 15.0  # Sidereal motion translation approximation 
        self.pulse_guide(direction, duration)