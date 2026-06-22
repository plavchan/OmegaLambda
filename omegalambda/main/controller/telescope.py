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
        self.live_connection.set()
        self.live_connection_lock = threading.Lock()

    def last_slew_status(self):
        return self.slewDone()
        
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
            time.sleep(5)
            # Connect the telescope hardware if not already connected
            self.Telescope.send_js("sky6RASCOMTele.Connect();")
            time.sleep(5)      
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
        with self.live_connection_lock:
            if self.Telescope:
                self.Telescope.send_js("sky6RASCOMTele.Disconnect();")
            self.live_connection.set()
        return True

    def _is_ready(self):
        """
        Blocking loop that holds execution until the telescope completes its current slew.
        """
        val=0
        with self.live_connection_lock:
            while val==0:
                # IsSlewComplete returns 0 if still moving, !=0 if done
                val = self.Telescope.send_js("var rest = sky6RASCOMTele.IsSlewComplete; rest;")
                print("isslewcomplete val:",val)
                try:
                    val = int(val)
                except:
                    val = 0
                time.sleep(5)
                if val != 0:
                    self.last_slew_status = 1
                else:  # this is a check on errant slews
                    if self.check_current_coords == False:
                        self.abort()
                        logging.critical("While thought to be slewing, telescope has slewed past limits, despite the final destination being within limits! Aborting slew!")
                        self.last_slew_status = -100
                        time.sleep(2)
                        self.live_connection.set()
                        return -100

    @property
    def status(self):
        """
        Exposes a telemetry status dictionary mapping real-time states 
        to satisfy OmegaLambda's background ThreadMonitor diagnostics.
        """
        
        # Pull real-time connection state from your active Event flag
        is_connected = self.live_connection.is_set()
       
        # Query if the mount is slewing (IsSlewComplete returns 0 if moving)
        if is_connected and self.Telescope:
            slew_val = self.Telescope.send_js("var res = sky6RASCOMTele.IsSlewComplete; res;")
            is_slewing = (slew_val == "0")
        else:
            is_slewing = False
            logging.error("Telescope not connected or no self.telescope in status call")

        # Build the exact status metadata structure expected by the framework
        retdict = {
             "connected": None,
             "slewing": None,
             "ra": None,
             "dec": None,
             "inbounds": None
        }
        if is_connected: 
             coords = self.get_coordinates()
             retdict["connected"] = is_connected
             retdict["slewing"] = is_slewing
             retdict["ra"] = coords.get("ra")
             retdict["dec"] = coords.get("dec")
             retdict["inbounds"] = self.check_current_coords()
        else:
             logging.error("Telescope not connected during status call")
        return retdict


    def abort(self):
        """
        Description
        -----------
        Aborts any slews that may be in progress.

        Returns
        -------
        None.

        """
        logging.warning('Aborting slew')
        with self.live_connection_lock:
            self.Telescope.send_js("sky6RASCOMTele.Abort();")        

    def park(self):
        """
        Parks the telescope to its resting safety orientation.
        """
        print("Parking scope...")
        with self.live_connection_lock:
            self._is_ready()
            # Turn tracking off natively before parking
            self.Telescope.send_js("sky6RASCOMTele.SetTracking(0, 1, 0.0, 0.0);")
            self.Telescope.send_js("sky6RASCOMTele.Park();")
            self._is_ready()

    def unpark(self):
        """
        Unparks the telescope mount.
        """
        print("Unparking scope...")
        with self.live_connection_lock:
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
            coordsaltaz = self.get_coordinatesAltAz()
            if coordsaltaz["alt"] is not None and coordsaltaz["az"] is not None:
                if coordsaltaz["alt"] < 10 or abs(coords["ra"])>8.0:
                     inbounds=False
                     self.last_slew_status = False
                else:
                     inbounds=True
            else:
                inbounds=False
                logging.debug("coordsaltaz is none")
            logging.debug(
                f"Current Telescope Coordinates -- "
                f"RA: {ra_hours:02d}:{ra_minutes:02d}:{ra_seconds:05.2f}, "
                f"DEC: {dec_degrees:02d}:{dec_minutes:02d}:{dec_seconds:04.1f}"
            )
            #self.status["inbounds"] = inbounds
            return True #inbounds
        else:
            logging.warning("ThreadMonitor failed to fetch telescope coordinates.")
            #self.status["connected"] = False
            return False

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
        #print(ra_raw,dec_raw)
        try:
            return {
                "ra": float(ra_raw),
                "dec": float(dec_raw)
            }
        except ValueError:
            logging.error("Could not parse coordinates from telescope socket in get_coordinates().")
            return {"ra": None, "dec": None}

    def get_coordinatesAltAz(self):
        """
        Queries the telescope position 
        Returns
        -------
        dict
            A dictionary tracking current 'alt' and 'azi'.
        """
        # Command TheSkyX to grab latest telemetry
        self.Telescope.send_js("sky6RASCOMTele.GetAzAlt();")
        
        # Pull values out via separate evaluated expressions
        alt_raw = self.Telescope.send_js("var res = sky6RASCOMTele.dAlt; res;")
        az_raw = self.Telescope.send_js("var res = sky6RASCOMTele.dAz; res;")
        #print(alt_raw,az_raw)
        try:
            return {
                "alt": float(alt_raw),
                "az": float(az_raw)
            }
        except ValueError:
            logging.error("Could not parse alt/az coordinates from telescope socket in get_coordinatesaltaz().")
            return {"alt": None, "az": None}

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

        with live_connection_lock:
            self.live_connection.clear()
            self._is_ready()        
            # Native async command sequence mapping to target variables
            self.Telescope.send_js("sky6RASCOMTele.Asynchronous = 1;\n")
            time.sleep(1)
            print(ra,dec)
            target_name = "automatedradec"
            cmd = f'sky6RASCOMTele.SlewToRaDec({ra}, {dec}, "{target_name}");\n'
            self.Telescope.send_js(cmd)
            # Wait until movement is finalized
            self._is_ready()
            # Set post-slew tracking state
            track_flag = 1 if tracking else 0
            self.Telescope.send_js(f"sky6RASCOMTele.SetTracking({track_flag}, 1, 0.0, 0.0);")
            coords = self.get_coordinates()
            if abs(ra - coords["ra"]) <= 0.05 and abs(dec - coords["dec"]) < 0.05:
                  self.last_slew_status = True
            else:
                  self.last_slew_status = False
            self.live_connection.set()
        return self.last_slew_status

    def slewAltAz(self, alt, az, tracking=True):
        """
        Asynchronously slews the telescope to target alt-az coordinates.

        Parameters
        -------
               tracking : bool, optional
            Whether standard sidereal tracking remains engaged after slew finishes. Default is True.
        """
        if alt < 8:
            logging.error(f"Invalid alt coordinate given: {alt}")
            return
        with self.live_connection_lock:
            self.live_connection.clear()
            self._is_ready()
            print("connection status in start of slew command: ",self.status["connected"])
            target_name = "automatedaltaz"
            # Native async command sequence mapping to target variables
            self.Telescope.send_js("sky6RASCOMTele.Asynchronous = 1;\n")
            time.sleep(1)
            print(alt,az)
            cmd = f'sky6RASCOMTele.SlewToAzAlt({az}, {alt},"{target_name}");\n'
            self.Telescope.send_js(cmd)
            # Wait until movement is finalized
            self._is_ready()
            # Set post-slew tracking state
            track_flag = 1 if tracking else 0
            self.Telescope.send_js(f"sky6RASCOMTele.SetTracking({track_flag}, 1, 0.0, 0.0);")
            coords = self.get_coordinatesAltAz()
            if abs(alt - coords["alt"]) <= 0.05 and abs(az - coords["az"]) < 0.05:
                  self.last_slew_status = True
            else:
                  self.last_slew_status = False
            self.live_connection.set()
        return self.last_slew_status


    def set_tracking(self, tracking=True):
        """
        Toggles telescope target tracking states.
        """
        track_flag = 1 if tracking else 0
        try:
             self.Telescope.send_js(f"sky6RASCOMTele.SetTracking({track_flag}, 1, 0.0, 0.0);")
        except (WinError):
             logging.debug("Could not set tracking")
        self.live_connection.set()
        return True

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
        logging.debug('Sending telescope pulse guide request...')    
        self.live_connection.clear()
        cmd = f"sky6RASCOMTele.PulseGuide({duration_ms}, {target_dir});"
        try:
            self.Telescope.send_js(cmd)
        except (WinError):
            logging.error('could not pulse guide')
            return False
        else:
            self._is_ready()
            self.live_connection.set()
            logging.info('Telescope is pulse guiding')
            return True

    def jog(self, direction, distance):
        """
        Jogs the telescope position using small fixed step increments.
        """
        # Retained logic interface utilizing pulse guide timing blocks to approximate step movement distances safely
        # Note: If your system configuration relies on guide rate values, adjust math ratios accordingly
        duration = distance / 15.0  # Sidereal motion translation approximation 
        logging.debug('Sending telescope jog request...')
        self.live_connection.clear()
        self.pulse_guide(direction, duration)