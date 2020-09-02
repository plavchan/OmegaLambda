import threading
import logging
import time
import subprocess
import pywintypes
import win32com.client

from ..common.util import conversion_utils
from .hardware import Hardware


class Telescope(Hardware):
    
    def __init__(self):
        """
        Initializes the telescope class as a subclass of Hardware.

        Returns
        -------
        None.

        """
        self.slew_done = threading.Event()
        self.movement_lock = threading.Lock()
        # Threading event sets flags and allows threads to interact with each other
        super(Telescope, self).__init__(name='Telescope')       # Calls Hardware.__init__ with the name 'Telescope'

    def check_connection(self):
        """
        Description
        -----------
        Overwrites base class.  Checks for telescope connection specifically.

        Returns
        -------

        """
        logging.info('Checking connection for the {}'.format(self.label))
        self.live_connection.clear()
        if not self.Telescope.Connected:
            self.Telescope.Connected = True
            self.live_connection.set()
        else:
            print("Already connected")

    def _class_connect(self):
        """
        Description
        -----------
        Overrides base hardware class (not implemented).
        Dispatches COM connection to telescope object and sets necessary parameters.
        Should only ever be called from within the run method.

        Returns
        -------
        BOOL
            True if successful, otherwise False.
        """
        try:
            self.Telescope = win32com.client.Dispatch("ASCOM.SoftwareBisque.Telescope")
            self.Telescope.SlewSettleTime = 1
            self.check_connection()
        except (AttributeError, pywintypes.com_error):
            logging.error('Could not connect to the telescope')
            return False
        else:
            print('Telescope has successfully connected')
        return True

    def __check_coordinate_limit(self, ra, dec, time=None):
        """

        Parameters
        ----------
        ra : FLOAT
            Target object's right ascension in hours.
        dec : FLOAT
            Target object's declination in degrees.
        time : CLASS INSTANCE OBJECT of DATETIME.DATETIME, optional
            Time at which these coordinates will need to be converted to Altitude/Azimuth. The default is None,
            which will convert them for the current date/time.

        Returns
        -------
        BOOL
            If True, the coordinates are within the physical limits of the telescope, and the
            slew may proceed.

        """
        (az, alt) = conversion_utils.convert_radec_to_altaz(ra, dec, self.config_dict.site_latitude,
                                                            self.config_dict.site_longitude, time)
        logging.debug('Checking coordinates for telescope slew...')
        if alt <= 15 or dec > 90:
            logging.debug('Coordinates not good.  Aborting slew.')
            return False
        else:
            logging.debug('Coordinates are good.  Starting slew')
            return True
        # TODO: Figure out if there are any other limits
       
    def _is_ready(self):
        """
        Description
        -----------
        Affirms that the telescope is done slewing and ready for another command before continuing.

        Returns
        -------
        None.

        """
        while self.Telescope.Slewing:
            time.sleep(1)
        if not self.Telescope.Slewing:
            return
          
    def park(self):
        """

        Returns
        -------
        BOOL
            True if the park was successful, False otherwise.

        """
        self.slew_done.clear()
        if self.Telescope.AtPark:
            self.slew_done.set()
            print("Telescope is at park")
            return True
        self._is_ready()
        with self.movement_lock:
            try:
                self.Telescope.Park()
            except Exception as exc:
                logging.error("Could not park telescope.  Exception: {}".format(exc))
                return False
            time.sleep(1)
            t = 0
            while self.Telescope.Tracking:
                try:
                    self.Telescope.Tracking = False
                except Exception as exc:
                    logging.error("Could not disable tracking.  Exception: {}".format(exc))
                time.sleep(5)
                t += 5
                if t >= 25:
                    logging.critical("Failed to disable telescope tracking. "
                                     "Gave up after {} attempts.".format(t // 5))
                    break
            logging.info('Telescope is parked, tracking off')
            self._is_ready()
            self.slew_done.set()
            return True
        
    def unpark(self):
        """

        Returns
        -------
        BOOL
            True if unpark was successful, False otherwise.

        """
        self._is_ready()
        try:
            with self.movement_lock:
                self.Telescope.Unpark()
                self.Telescope.Tracking = True
        except: 
            print("ERROR: Error unparking telescope tracking")
            return False
        else: 
            print("Telescope is unparked; tracking at sidereal rate")
            logging.info("Telescope is unparked, tracking on")
            return True
    
    def slew(self, ra, dec, tracking=True):
        """

        Parameters
        ----------
        ra : FLOAT
            Right ascension of target in hours.
        dec : FLOAT
            Declination of target in degrees.
        tracking : BOOL, optional
            Whether to turn tracking on or off. The default is True for RA/Dec slews.

        Returns
        -------
        BOOL
            True if slew succeeded, False otherwise.

        """
        self.slew_done.clear()
        (ra, dec) = conversion_utils.convert_j2000_to_apparent(ra, dec)
        # Telescope internally uses apparent epoch coordinates, but we input in J2000
        if self.__check_coordinate_limit(ra, dec) is False:
            logging.error("Coordinates are outside of physical slew limits.")
            return False
        else:
            self._is_ready()
            try:
                with self.movement_lock:
                    logging.info('Slewing to RA/Dec')
                    self.Telescope.SlewToCoordinates(ra, dec)
                    self.Telescope.Tracking = tracking
            except:
                logging.error("Error slewing to target")
            self._is_ready()
            if abs(self.Telescope.RightAscension - ra) <= 0.05 and abs(self.Telescope.Declination - dec) <= 0.05:
                self.slew_done.set()
                return True
            else:
                return False
    
    def pulse_guide(self, direction, duration):
        """

        Parameters
        ----------
        direction : STR
            Direction that the telescope should pulse guide.  Up, down, left, or right.
        duration : INT
            Duration in seconds that the telescope should pulse guide for.

        Returns
        -------
        BOOL
            True if successful, False otherwise.

        """
        self.slew_done.clear()
        direction_key = {"up": 0, "down": 1, "left": 2, "right": 3}
        # Converts str to int, used by internal telescope calls
        
        if direction in direction_key:
            direction_num = direction_key[direction]
        else:
            logging.error("Invalid pulse guide direction")
            return False
        
        duration *= 1000
        # Convert seconds to milliseconds, used by internal telescope calls
        self._is_ready()
        try:
            with self.movement_lock:
                self.Telescope.PulseGuide(direction_num, duration)
        except:
            logging.error("Could not pulse guide")
            return False
        else:
            self._is_ready()
            self.slew_done.set()
            logging.info('Telescope is pulse guiding')
            return True
            
    def jog(self, direction, distance):
        """

        Parameters
        ----------
        direction : STR
            Direction to jog the telescope.  Up, down, left, or right.
        distance : INT
            Distance to jog the telescope in arcseconds.

        Returns
        -------
        None.

        """
        self.slew_done.clear()
        logging.debug('Sending telescope jog request...')
        rates_key = {**dict.fromkeys(["up", "down"], self.Telescope.GuideRateDeclination),
                     **dict.fromkeys(["left", "right"], self.Telescope.GuideRateRightAscension)}
        # Dictionaries to convert direction str to distance
        distance_key = {**dict.fromkeys(["up", "left"], distance),
                        **dict.fromkeys(["down", "right"], -distance)}
        
        if direction in rates_key:
            rate = rates_key[direction]
            distance = distance_key[direction]
        else:
            logging.error('Invalid jog direction')
            return
        if distance < 30*60:                            # Less than 30', pulse guide
            duration = (abs(distance)/3600)/rate
            logging.debug('Calculated Pulse Guide Duration: {} milliseconds'.format(duration*1000))
            self.pulse_guide(direction, duration)
            
        elif distance >= 30*60:                         # More than 30', slew normally
            if direction in ("up", "down"):
                self.slew(self.Telescope.RightAscension, self.Telescope.Declination + distance)
            elif direction in ("left", "right"):
                self.slew(self.Telescope.RightAscension + distance, self.Telescope.Declination)
            logging.info('Telescope is jogging')
    
    def slewaltaz(self, az, alt, time=None, tracking=False):
        """

        Parameters
        ----------
        az : FLOAT
            Azimuth in degrees of the target to slew to.
        alt : FLOAT
            Altitude in degrees of the target to slew to.
        time : CLASS INSTANCE OBJECT of DATETIME.DATETIME, optional
            The time for which the conversion to ra/dec should be done. The default is None,
            which converts them for the current time.
        tracking : BOOL, optional
            Whether to set the tracking on or off after slewing. The default is False for Alt/Az slews.

        Returns
        -------
        None
            Returns nothing.  If there is an error, it returns a print statement that the altitude is below 15 degrees.

        """
        if alt <= 15:
            return logging.error("Cannot slew below 15 degrees altitude.")
        else:
            with self.movement_lock:
                (ra, dec) = conversion_utils.convert_altaz_to_radec(az, alt, self.config_dict.site_latitude,
                                                                    self.config_dict.site_longitude, time)
                self.slew(ra, dec, tracking)
                logging.info('Slewing to Alt/Az')
    
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
        self.Telescope.AbortSlew()
        
    def disconnect(self):
        """
        Description
        -----------
        Disconnects the telescope.  Always park before disconnecting!

        Returns
        -------
        BOOL
            True if disconnecting was successful, False otherwise.

        """
        logging.debug('Disconnecting telescope...')
        self._is_ready()
        if self.Telescope.AtPark:
            try: 
                self.Telescope.Connected = False
                self.live_connection.clear()
                subprocess.call("taskkill /f /im TheSkyX.exe")
                # This is the only way it will actually disconnect from TheSkyX so far
            except:
                logging.error("Could not disconnect from telescope")
            else:
                logging.info('Telescope disconnected'); return True
        else: 
            logging.warning("Telescope is not parked.")
            return False
        
        
# Don't know what the cordwrap functions were all about in the deprecated telescope file?
