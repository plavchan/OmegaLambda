import datetime
import time
import os
import re
import logging
import subprocess
# import threading

from ..common.util import time_utils, conversion_utils
from ..common.IO import config_reader
from ..common.datatype import filter_wheel
from ..controller.camera import Camera
from ..controller.telescope import Telescope
from ..controller.dome import Dome
from ..controller.flatfield_lamp import FlatLamp
from .calibration import Calibration
from .condition_checker import Conditions


class ObservationRun:
    def __init__(self, observation_request_list, image_directory, shutdown_toggle, calibration_toggle):
        """
        Initializes the observation run.

        Parameters
        ----------
        observation_request_list : LIST
            List of observation tickets.
        image_directory : STR
            Directory to which the images will be saved to.
        shutdown_toggle : BOOL
            Whether or not to shut down after finished with observations.
        calibration_toggle : BOOL
            Whether or not to take calibration images at the specified calibration time in the configuration
            file.

        Returns
        -------
        None.
        """
        # Basic parameters
        self.image_directory = image_directory
        self.observation_request_list = observation_request_list
        self.calibrated_tickets = [0] * len(observation_request_list)
        self.current_ticket = None
        self.shutdown_toggle = shutdown_toggle
        self.calibration_toggle = calibration_toggle
        self.tz = observation_request_list[0].start_time.tzinfo

        # Initializes all relevant hardware
        self.camera = Camera()
        self.telescope = Telescope()
        self.dome = Dome()
        self.conditions = Conditions()
        self.flatlamp = FlatLamp()

        # Initializes higher level structures - focuser, guider, and calibration
        self.calibration = Calibration(self.camera, self.flatlamp, self.image_directory)

        # Initializes config objects
        self.filterwheel_dict = filter_wheel.get_filter().filter_position_dict()
        self.config_dict = config_reader.get_config()

        # Starts the threads
        self.conditions.start()
        self.camera.start()
        self.telescope.start()
        self.dome.start()
        self.flatlamp.start()
        self.calibration.start()

    def everything_ok(self):
        """
        Description
        -----------
        Checks hardware connections and all outside conditions (humidity, wind, rain,
                                                                sun elevation, and cloud coverage)

        Returns
        -------
        bool
            If False, something has gone wrong, and so the observing will have to stop. Otherwise, conditions are
            good to continue observation.

        """
        check = True
        connections = {
            'Camera': self.camera,
            'Telescope': self.telescope,
            'Dome': self.dome,
            'FlatLamp': self.flatlamp
        }
        message = ''
        for key, value in connections.items():
            if not value.live_connection.wait(timeout=10):
                message += key + ' '
                check = False
        if message:
            logging.error('Hardware connection timeout: {}'.format(message))

        if self.conditions.weather_alert.isSet():
            if (self.config_dict.calibration_time == "end") and (self.calibration_toggle is True):
                calibration = True
            else:
                calibration = False
            self._shutdown_procedure(calibration=calibration)
            if (self.current_ticket == self.observation_request_list[-1] or self.current_ticket is None) \
                    and (self.observation_request_list[-1].end_time < datetime.datetime.now(self.tz)
                         + datetime.timedelta(hours=3)):
                logging.info('Close to end time of final ticket.  Stopping the code.')
                self.stop_threads()
                return False
            if self.conditions.sun:
                sunset_time = conversion_utils.get_sunset(datetime.datetime.now(self.tz),
                                                          self.config_dict.site_latitude,
                                                          self.config_dict.site_longitude)
                logging.info('The Sun has risen above the horizon...observing will stop until the Sun sets again '
                             'at {}.'.format(sunset_time.strftime('%Y-%m-%d %H:%M:%S%z')))
                time.sleep(60*self.config_dict.min_reopen_time)
                sunset_epoch_milli = time_utils.datetime_to_epoch_milli_converter(sunset_time)
                current_epoch_milli = time_utils.datetime_to_epoch_milli_converter(datetime.datetime.now(self.tz))
                if sunset_epoch_milli > current_epoch_milli:
                    time.sleep((sunset_epoch_milli - current_epoch_milli)/1000)
                logging.info('The Sun should now be setting again...observing will resume shortly.')
                if not self.conditions.weather_alert.isSet():
                    check = True
                    if not self.current_ticket:
                        self.observe()
                    elif self.current_ticket.end_time > datetime.datetime.now(self.tz):
                        self._startup_procedure()
                        self._ticket_slew(self.current_ticket)
                    elif self.current_ticket != self.observation_request_list[-1]:
                        self._startup_procedure()
                else:
                    print('Weather is still too poor to resume observing.')
                    self.everything_ok()
            else:
                time.sleep(60*self.config_dict.min_reopen_time)
                while self.conditions.weather_alert.isSet():
                    time.sleep(self.config_dict.weather_freq*60)
                if not self.conditions.weather_alert.isSet():
                    check = True
                    if self.current_ticket.end_time > datetime.datetime.now(self.tz):
                        self._startup_procedure()
                        self._ticket_slew(self.current_ticket)
                    elif self.current_ticket != self.observation_request_list[-1]:
                        self._startup_procedure()
        return check

    def _startup_procedure(self, calibration=False):
        """
        Parameters
        ----------
        calibration : BOOL, optional
            Whether or not to take calibration images at the beginning
            of the night. The default is False.

        Returns
        -------
        Initial_shutter : INT
            The position of the shutter before observing started.
            0 = open, 1 = closed, 2 = opening, 3 = closing, 4 = error.
            -1 = failed hardware/weather check.

        """
        initial_check = self.everything_ok()

        self.camera.onThread(self.camera.cooler_set, True)
        self.dome.onThread(self.dome.shutter_position)
        time.sleep(2)
        initial_shutter = self.dome.shutter
        if initial_shutter in (1, 3, 4) and initial_check is True:
            if calibration:
                self.camera.onThread(self.camera.cooler_ready)
                self.camera.cooler_settle.wait()
                print('Taking darks and flats...')
                self.take_calibration_images(beginning=True)
            self.dome.onThread(self.dome.move_shutter, 'open')
            self.dome.onThread(self.dome.home)
        elif not initial_check:
            if not self.conditions.weather_alert.isSet():
                self.shutdown()
            return -1
        self.telescope.onThread(self.telescope.unpark)
        self.camera.onThread(self.camera.cooler_ready)
        self.dome.onThread(self.dome.slave_dome_to_scope, True)
        return initial_shutter

    def _ticket_slew(self, ticket):
        """

        Parameters
        ----------
        ticket : ObservationTicket Object
            Created from json_reader and object_reader.

        Returns
        -------
        bool
            True if slew was successful, otherwise False.

        """
        self.telescope.onThread(self.telescope.slew, ticket.ra, ticket.dec)
        slew = self.telescope.slew_done.wait()
        if not slew:
            logging.error('Telescope slew has failed.  Retrying...')
            self.telescope.onThread(self.telescope.slew, ticket.ra, ticket.dec)
            slew2 = self.telescope.slew_done.wait()
            if not slew2:
                logging.critical('Telescope still cannot slew to target.  Cannot continue observing.')
                return False
        return True

    def observe(self):
        """
        Description
        ----------
        Makes sure the dome, shutter, camera are ready to begin observation,
        and the start time has passed before beginning observation.  Then it loops
        through all tickets and starts the necessary procedures.

        Returns
        -------
        None.
        """
        if (self.config_dict.calibration_time == "start") and (self.calibration_toggle is True):
            calibration = True
        else:
            calibration = False

        tz_0 = self.observation_request_list[0].start_time.tzinfo
        current_time = datetime.datetime.now(tz_0)
        if self.observation_request_list[0].start_time > current_time:
            print("It is not the start time {} of {} observation, "
                  "waiting till start time.".format(self.observation_request_list[0].start_time.isoformat(),
                                                    self.observation_request_list[0].name))
            current_epoch_milli = time_utils.datetime_to_epoch_milli_converter(current_time)
            start_time_epoch_milli = time_utils.datetime_to_epoch_milli_converter(
                self.observation_request_list[0].start_time)
            time.sleep((start_time_epoch_milli - current_epoch_milli) / 1000)

        initial_shutter = self._startup_procedure(calibration)
        if initial_shutter == -1:
            return

        for ticket in self.observation_request_list:
            self.current_ticket = ticket
            if not self.everything_ok():
                if not self.conditions.weather_alert.isSet():
                    self.shutdown()
                return
            self.crash_check('TheSkyX.exe')
            self.crash_check('ASCOMDome.exe')
            if not self._ticket_slew(ticket):
                return
            if initial_shutter in (1, 3, 4):
                self.dome.move_done.wait()
                self.dome.shutter_done.wait()
            self.camera.cooler_settle.wait()

            self.tz = ticket.start_time.tzinfo
            current_time = datetime.datetime.now(self.tz)
            if ticket.start_time > current_time:
                print("It is not the start time {} of {} observation, "
                      "waiting till start time.".format(ticket.start_time.isoformat(), ticket.name))
                current_epoch_milli = time_utils.datetime_to_epoch_milli_converter(current_time)
                start_time_epoch_milli = time_utils.datetime_to_epoch_milli_converter(ticket.start_time)
                time.sleep((start_time_epoch_milli - current_epoch_milli)/1000)
            if ticket.end_time < current_time:
                print("the end time {} of {} observation has already passed. "
                      "Skipping to next target.".format(ticket.end_time.isoformat(), ticket.name))
                continue

            if not self.everything_ok():
                if not self.conditions.weather_alert.isSet():
                    self.shutdown()
                return

            input("The program is ready to start taking images of {}.  Please take this time to "
                  "check the focus and pointing of the target.  When you are ready, press Enter: ".format(ticket.name))
            (taken, total) = self.run_ticket(ticket)
            print("{} out of {} exposures were taken for {}.  Moving on to next target.".format(taken, total,
                                                                                                ticket.name))

        if (self.config_dict.calibration_time == "end") and (self.calibration_toggle is True):
            calibration = True
        else:
            calibration = False
        self.shutdown(calibration)

    def run_ticket(self, ticket):
        """
        Parameters
        ----------
        ticket : ObservationTicket Object
            The observation ticket object with information useful to
            the observing run.

        Returns
        -------
        img_count: INT
            Number of images taken.
        ticket.num: INT
            The total number of images that are specified on the
            observation ticket.
        """
        ticket.exp_time = [ticket.exp_time] if type(ticket.exp_time) in (int, float) else ticket.exp_time
        ticket.filter = [ticket.filter] if type(ticket.filter) is str else ticket.filter
        if ticket.cycle_filter:
            img_count = self.take_images(ticket.name, ticket.num, ticket.exp_time,
                                         ticket.filter, ticket.end_time, self.image_directory,
                                         True)
            return img_count, ticket.num

        else:
            img_count = 0
            if len(ticket.exp_time) <= 1:
                ticket.exp_time *= len(ticket.filter)
            for i in range(len(ticket.filter)):
                img_count_filter = self.take_images(ticket.name, ticket.num, [ticket.exp_time[i]],
                                                    [ticket.filter[i]], ticket.end_time, self.image_directory,
                                                    False)
                img_count += img_count_filter
            return img_count, ticket.num * len(ticket.filter)

    def take_images(self, name, num, exp_time, _filter, end_time, path, cycle_filter):
        """
        Parameters
        ----------
        name : STR
            Name of target to be observed.
        num : INT
            Total number of exposures to be taken during the night.
        exp_time : LIST
            The exposure times of each image.
        _filter : LIST, STR
            The filters to be used during the night.
        end_time : datetime.datetime Object
            The end time of the observation session, set
            in the observation ticket.
        path : STR
            The image save path.
        cycle_filter : BOOL
            If True, camera will cycle filter after each exposre,
            if False, camera will cycle filter after num value has been reached.

        Returns
        -------
        i : INT
            The number of images taken for the current ticket.
        """
        num_filters = len(_filter)
        num_exptimes = len(exp_time)
        # num_filters and num_exptimes should always be equal, not sure if we need both
        image_num = 1
        names_list = []
        image_base = {}
        i = 0
        while i < num:
            logging.debug('In take_images loop')
            if end_time <= datetime.datetime.now(self.tz):
                print("The observations end time of {} has passed.  "
                      "Stopping observation of {}.".format(end_time, name))
                break
            if not self.everything_ok():
                break
            current_filter = _filter[i % num_filters]
            current_exp = exp_time[i % num_exptimes]
            image_name = "{0:s}_{1:.3f}s_{2:s}-{3:04d}.fits".format(name, current_exp, str(current_filter).upper(),
                                                                    image_num)
            
            if i == 0 and os.path.exists(os.path.join(path, image_name)):
                # Checks if images already exist (in the event of a crash)
                for f in _filter:
                    names_list = [0]
                    for fname in os.listdir(path):
                        if n := re.search('{0:s}_{1:.3f}s_{2:s}-(.+?).fits'.format(name, current_exp, str(f).upper()),
                                          fname):
                            names_list.append(int(n.group(1)))
                    image_base[f] = max(names_list) + 1
                
                image_name = "{0:s}_{1:.3f}s_{2:s}-{3:04d}.fits".format(name, current_exp, str(current_filter).upper(),
                                                                        image_base[current_filter])
                
            self.camera.onThread(self.camera.expose, 
                                 current_exp, self.filterwheel_dict[current_filter],
                                 os.path.join(path, image_name), "light")
            self.camera.image_done.wait(timeout=int(current_exp)*2 + 60)
            
            if self.crash_check('MaxIm_DL.exe'):
                continue
            
            if cycle_filter:
                if names_list:
                    image_num = int(image_base[_filter[(i + 1) % num_filters]] + ((i + 1) / num_filters))
                else:
                    image_num = int(1 + ((i + 1)/num_filters))
            elif not cycle_filter:
                if names_list:
                    image_num = image_base[_filter[(i + 1) % num_filters]] + (i + 1)
                else:
                    image_num += 1
            i += 1
        return i
    
    def crash_check(self, program):
        """
        Description
        -----------
        Checks to see if any important programs are not responding, and if so,
        restarts them.

        Parameters
        ----------
        program : STR
            Name of the program to check for.

        Returns
        -------
        bool
            True if the program is not responding and needs to be restarted, otherwise
            False.

        """
        prog_dict = {'MaxIm_DL.exe': [self.camera, Camera], 'TheSkyX.exe': [self.telescope, Telescope],
                     'ASCOMDome.exe': [self.dome, Dome]}
        if program not in prog_dict.keys():
            logging.error('Unrecognized program name to perform a crash check for.')
            return False
        cmd = 'tasklist /FI "IMAGENAME eq %s" /FI "STATUS eq running"' % program
        status = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
        responding = program in str(status)
            
        if not responding:
            prog_dict[program][0].crashed.set()
            logging.error('{} is not responding.  Restarting...'.format(program))
            time.sleep(5)
            prog_dict[program][0].crashed.clear()
            subprocess.call('taskkill /f /im {}'.format(program))
            time.sleep(5)
            prog_dict[program][0] = prog_dict[program][1]()
            prog_dict[program][0].start()
            time.sleep(5)
            return True
        else:
            return False
        
    def take_calibration_images(self, beginning=False):
        """
        Description
        -----------
        Takes flats and darks for the current observation ticket and
        any previous ones.

        Parameters
        ----------
        beginning : BOOL, optional
            True if taking images before observations start, otherwise False. The default is False.

        Returns
        -------
        None.

        """
        for i in range(len(self.observation_request_list)):
            if self.calibrated_tickets[i]:
                continue
            self.calibration.onThread(self.calibration.take_flats, self.observation_request_list[i])
            self.calibration.flats_done.wait()
            self.calibration.onThread(self.calibration.take_darks, self.observation_request_list[i])
            self.calibration.darks_done.wait()
            self.calibrated_tickets[i] = 1
            if self.current_ticket == self.observation_request_list[i] and beginning is False:
                break
    
    def shutdown(self, calibration=False):
        """
        Description
        -----------
        Decides whether or not to shut down, and whether or not to take calibration images.

        Parameters
        ----------
        calibration : BOOL, optional
            Whether or not to take calibration images. The default is False.

        Returns
        -------
        None.

        """
        if self.shutdown_toggle or self.conditions.weather_alert.isSet():
            self._shutdown_procedure(calibration=calibration)
            time.sleep(1)
            self.stop_threads()
        else:
            return
        
    def stop_threads(self):
        """
        Description
        -----------
        Stops all of the hardware threads.

        Returns
        -------
        None.

        """
        self.camera.onThread(self.camera.disconnect)
        self.telescope.onThread(self.telescope.disconnect)
        self.dome.onThread(self.dome.disconnect)
        self.flatlamp.onThread(self.flatlamp.disconnect)

        self.conditions.stop.set()
        self.camera.onThread(self.camera.stop)
        self.telescope.onThread(self.telescope.stop)
        self.dome.onThread(self.dome.stop)
        self.flatlamp.onThread(self.flatlamp.stop)
        self.calibration.onThread(self.calibration.stop)
        time.sleep(5)
    
    def _shutdown_procedure(self, calibration):
        """
        Description
        ----------
        Safely shuts down the telescope, camera, and dome

        Parameters
        ----------
        calibration : BOOL
            Whether or not to take calibration images at the end

        Returns
        -------
        None.
        """
        print("Shutting down observatory.")
        self.dome.onThread(self.dome.slave_dome_to_scope, False)
        self.telescope.onThread(self.telescope.park)
        self.dome.onThread(self.dome.park)
        self.dome.onThread(self.dome.move_shutter, 'close')
        time.sleep(1)
        self.telescope.slew_done.wait()
        self.dome.move_done.wait()
        self.dome.shutter_done.wait()
        if calibration:
            print('Taking flats and darks...')
            self.take_calibration_images()
        
        self.camera.onThread(self.camera.cooler_set, False)
