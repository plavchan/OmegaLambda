import threading
import logging
import time
import subprocess
import pywintypes
import win32com.client

from ..common.util import conversion_utils
from ..common.util import time_utils
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
        self.slew_done.set()
        self.movement_lock = threading.Lock()
        self.last_slew_status = None
        self.status = True
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
            logging.info("Already connected")

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
            logging.info('Telescope has successfully connected')
        return True

    def __check_coordinate_limit(self, ra, dec, time=None, verbose=0):
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
        verbose : INT
            0 for no logging messages, 1 for logging messages

        Returns
        -------
        BOOL
            If True, the coordinates are within the physical limits of the telescope, and the
            slew may proceed.

        """
        lst = time_utils.get_local_sidereal_time(self.config_dict.site_longitude, time)
        ha = (lst - ra) % 24 # in hours
        if ha > 12:
            ha -= 24
        (az, alt) = conversion_utils.convert_radec_to_altaz(ra, dec, self.config_dict.site_latitude,
                                                            self.config_dict.site_longitude, time)

        if verbose:
            logging.debug('Telescope Coordinates: ' + str(ra) + ' ' + str(dec))
            logging.debug('Telescope Alt/Az: ' + str(alt) + ' ' + str(az))
        if (alt <= 15) or (dec > 90) or (abs(ha) > 8.75):
            msg = "Altitude less than 15 degrees" if (alt <= 15) else "Declination above 90 degrees" if (dec > 90) else \
                "Hour angle = {}h > 8h 45m".format(ha) if (abs(ha) > 8.75) else "None"
            logging.error('Coordinates not good.  Reason: {}'.format(msg))
            return False
        else:
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

    def check_current_coords(self):
        ra = self.Telescope.RightAscension
        dec = self.Telescope.Declination
        check = self.__check_coordinate_limit(ra, dec)
        self.status = check
        return self.status
          
    def park(self, coord_check_delay_ms=0):
        """

        Returns
        -------
        BOOL
            True if the park was successful, False otherwise.

        """
        self.slew_done.clear()
        if self.Telescope.AtPark:
            self.slew_done.set()
            logging.info("Telescope is at park")
            return True
        self._is_ready()
        try:
            # self.Telescope.Park()
            park_status = self.slewaltaz(self.config_dict.telescope_park_az, self.config_dict.telescope_park_alt, tracking=False,
                                         coord_check_delay_ms=coord_check_delay_ms)
        except (AttributeError, pywintypes.com_error) as exc:
            logging.error("Could not park telescope.  Exception: {}".format(exc))
            return False
        if park_status == -100:
            self.slew_done.set()
            return park_status
        time.sleep(1)
        t = 0
        while self.Telescope.Tracking:
            try:
                self.Telescope.Tracking = False
            except (AttributeError, pywintypes.com_error) as exc:
                logging.error("Could not disable tracking.  Exception: {}".format(exc))
            time.sleep(5)
            t += 5
            if t >= 25:
                logging.critical("Failed to disable telescope tracking. "
                                 "Gave up after {} attempts.".format(t // 5))
                break
        self._is_ready()
        with self.movement_lock:
            try:
                self.Telescope.Park()
            except (AttributeError, pywintypes.com_error) as exc:
                logging.error("Could not park telescope.  Exception: {}".format(exc))
                return False
        logging.info('Telescope is parked, tracking off')
        self._is_ready()
        self.slew_done.set()
        return park_status
        
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
        except (AttributeError, pywintypes.com_error):
            logging.error("Error unparking telescope or tracking")
            return False
        else: 
            logging.info("Telescope is unparked; tracking at sidereal rate")
            logging.info("Telescope is unparked, tracking on")
            return True
    
    def slew(self, ra, dec, tracking=True, coord_check_delay_ms=0):
        """

        Parameters
        ----------
        ra : FLOAT
            Right ascension of target in hours.
        dec : FLOAT
            Declination of target in degrees.
        tracking : BOOL, optional
            Whether to turn tracking on or off. The default is True for RA/Dec slews.
        coord_check_delay_ms : FLOAT, optional
            Delay time in milliseconds after the slew starts before coordinates are checked
            for validity.  This is necessary in case the starting position is out of bounds.

        Returns
        -------
        BOOL
            True if slew succeeded, False otherwise.

        """
        self.slew_done.clear()
        (ra, dec) = conversion_utils.convert_j2000_to_apparent(ra, dec)
        # Telescope internally uses apparent epoch coordinates, but we input in J2000
        if self.__check_coordinate_limit(ra, dec, verbose=1) is False:
            logging.error("Coordinates are outside of physical slew limits.")
            self.last_slew_status = False
        else:
            self._is_ready()
            try:
                with self.movement_lock:
                    logging.info('Slewing to RA/Dec')
                    self.Telescope.SlewToCoordinatesAsync(ra, dec)
                    if coord_check_delay_ms > 0:
                        time.sleep(coord_check_delay_ms/1000)
                    while self.Telescope.Slewing:
                        in_limits = self.__check_coordinate_limit(self.Telescope.RightAscension, self.Telescope.Declination, verbose=0)
                        if not in_limits:
                            self.abort()
                            logging.critical('Telescope has slewed past limits, despite the final destination being within limits!'
                                             ' aborting slew!')
                            self.Telescope.Tracking = False
                            self.last_slew_status = -100
                            time.sleep(2)
                            self.slew_done.set()
                            return -100
                        time.sleep(.1)
                    self.Telescope.Tracking = tracking
                    time.sleep(2)
            except (AttributeError, pywintypes.com_error):
                logging.debug("ASCOM Error slewing to target.  You may safely ignore this warning.")
            self._is_ready()
            if abs(self.Telescope.RightAscension - ra) <= 0.05 and abs(self.Telescope.Declination - dec) <= 0.05:
                self.last_slew_status = True
            else:
                self.last_slew_status = False
        self.slew_done.set()
        return self.last_slew_status

    def set_tracking(self, tracking):
        try:
            with self.movement_lock:
                logging.info('Setting telescope tracking to {}'.format(str(tracking)))
                self.Telescope.Tracking = tracking
        except (AttributeError, pywintypes.com_error):
            logging.error('Could not set telescope tracking!')
        self._is_ready()
        return True
    
    def pulse_guide(self, direction, duration):
        """

        Parameters
        ----------
        direction : STR
            Direction that the telescope should pulse guide.  north, south, east, or west.
        duration : INT
            Duration in seconds that the telescope should pulse guide for.

        Returns
        -------
        BOOL
            True if successful, False otherwise.

        """
        self.slew_done.clear()
        direction_key = {"north": 0, "south": 1, "east": 2, "west": 3}
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
        except (AttributeError, pywintypes.com_error):
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
            Direction to jog the telescope.  North, south, east, or west.
        distance : INT
            Distance to jog the telescope in arcseconds.

        Returns
        -------
        None.

        """
        self.slew_done.clear()
        logging.debug('Sending telescope jog request...')
        rates_key = {**dict.fromkeys(["north", "south"], self.Telescope.GuideRateDeclination),
                     **dict.fromkeys(["east", "west"], self.Telescope.GuideRateRightAscension)}
        # Dictionaries to convert direction str to distance
        distance_key = {**dict.fromkeys(["north", "east"], distance),
                        **dict.fromkeys(["south", "west"], -distance)}
        
        if direction in rates_key:
            rate = rates_key[direction]
            distance = distance_key[direction]
        else:
            logging.error('Invalid jog direction')
            return
        if abs(distance) < 30*60:                            # Less than 30', pulse guide
            duration = (abs(distance)/3600)/rate
            logging.debug('Calculated Pulse Guide Duration: {} milliseconds'.format(duration*1000))
            self.pulse_guide(direction, duration)
            
        elif abs(distance) >= 30*60:                         # More than 30', slew normally
            if direction in ("north", "south"):
                self.slew(self.Telescope.RightAscension, self.Telescope.Declination + distance/3600)
            elif direction in ("east", "west"):
                self.slew(self.Telescope.RightAscension + distance/(15*3600), self.Telescope.Declination)
            logging.info('Telescope is jogging')
    
    def slewaltaz(self, az, alt, time=None, tracking=False, coord_check_delay_ms=0):
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
        slew : BOOL
            Whether or not slew was successful.

        """
        (ra, dec) = conversion_utils.convert_altaz_to_radec(az, alt, self.config_dict.site_latitude,
                                                            self.config_dict.site_longitude, time)
        (ra, dec) = conversion_utils.convert_apparent_to_j2000(ra, dec)
        slew = self.slew(ra, dec, tracking, coord_check_delay_ms=coord_check_delay_ms)
        logging.info('Slewing to Alt/Az')
        return slew
    
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
            except (AttributeError, pywintypes.com_error):
                logging.error("Could not disconnect from telescope")
            else:
                logging.info('Telescope disconnected')
                return True
        else: 
            logging.warning("Telescope is not parked.")
            return False
        
        
# Don't know what the cordwrap functions were all about in the deprecated telescope file?
