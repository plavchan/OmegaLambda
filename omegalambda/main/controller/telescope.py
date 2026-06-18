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

    @property
    def status(self):
        """
        Exposes a telemetry status dictionary mapping real-time states 
        to satisfy OmegaLambda's background ThreadMonitor diagnostics.
        """
        coords = self.get_coordinates()
        
        # Pull real-time connection state from your active Event flag
        is_connected = self.live_connection.is_set()
        
        # Query if the mount is slewing (IsSlewComplete returns 0 if moving)
        if is_connected and self.Telescope:
            slew_val = self.Telescope.send_js("var res = sky6RASCOMTele.IsSlewComplete; res;")
            is_slewing = (slew_val == "0")
        else:
            is_slewing = False

        # Build the exact status metadata structure expected by the framework
        #return {
        #    "connected": is_connected,
        #    "slewing": is_slewing,
        #    "ra": coords.get("ra"),
        #    "dec": coords.get("dec")
        #}
        if is_connected:
             return True 
        else:
             return False


    @property
    def slew_done(self):
        """
        Exposes a property mimicking a threading event object structure 
        to ensure compatibility with OmegaLambda's automated ThreadMonitor handlers.
        """
        # Define an inner structural helper container class with a custom wait attribute
        class SlewStatusWrapper:
            def __init__(self, telescope_obj):
                self._t = telescope_obj

            def is_set(self):
                """Returns True if the telescope is stationary and the slew is finished."""
                if not self._t.Telescope:
                    return True
                # IsSlewComplete returns 0 if still moving, 1 if done
                val = self._t.Telescope.send_js("var res = sky6RASCOMTele.IsSlewComplete; res;")
                return val == "1"

            def wait(self, timeout=None):
                """
                Blocks the caller until the telescope finishes slewing or 
                the specified timeout expires.
                """
                start_time = time.time()
                while not self.is_set():
                    if timeout and (time.time() - start_time) > timeout:
                        return False
                    time.sleep(0.2)
                return True

        # Instantiates and returns the status container object
        return SlewStatusWrapper(self)


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
            # 1. Format RA (coords["ra"] is already in decimal hours)
            ra_hours = int(coords["ra"])
            ra_minutes = int((coords["ra"] - ra_hours) * 60)
            ra_seconds = (coords["ra"] - ra_hours - ra_minutes/60.0) * 3600
            
            # 2. Format DEC (coords["dec"] is in decimal degrees)
            dec_abs = abs(coords["dec"])
            dec_degrees = int(dec_abs)
            dec_minutes = int((dec_abs - dec_degrees) * 60)
            dec_seconds = (dec_abs - dec_degrees - dec_minutes/60.0) * 3600
            if coords["dec"] < 0:
                dec_degrees = -dec_degrees

            logging.debug(
                f"Current Telescope Coordinates -- "
                f"RA: {ra_hours:02d}:{ra_minutes:02d}:{ra_seconds:05.2f}, "
                f"DEC: {dec_degrees:02d}:{dec_minutes:02d}:{dec_seconds:04.1f}"
            )
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
        cmd = f"sky6RASCOMTele.SlewToRaDec({ra}, {dec}, 'Target Slew');"
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