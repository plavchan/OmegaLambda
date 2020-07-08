import datetime
import time
import os
import math
import re
import logging
import subprocess
import threading
import numpy as np

from ..common.util import time_utils, conversion_utils, filereader_utils
from ..common.IO import config_reader
from ..common.datatype import filter_wheel
from ..controller.camera import Camera
from ..controller.telescope import Telescope
from ..controller.dome import Dome
from ..controller.focuser_control import Focuser
from ..controller.focuser_procedures import FocusProcedures
from ..controller.flatfield_lamp import FlatLamp
from .calibration import Calibration
#from .guider import Guider
from .condition_checker import Conditions
    
class ObservationRun():
    def __init__(self, observation_request_list, image_directory, shutdown_toggle):
        '''

        :param observation_request_list: List of ObservationTickets
        '''
        self.image_directory = image_directory
        self.observation_request_list = observation_request_list
        self.calibrated_tickets = np.zeros(len(observation_request_list))
        self.current_ticket = None
        self.shutdown_toggle = shutdown_toggle
        self.tz = observation_request_list[0].start_time.tzinfo
        self.FWHM = None
        self.camera = Camera()
        self.telescope = Telescope()
        self.dome = Dome()
        self.conditions = Conditions()
        self.focuser = Focuser()
        self.flatlamp = FlatLamp()
        self.focus_procedures = FocusProcedures(self.focuser, self.camera)
        self.calibration = Calibration(self.camera, self.flatlamp, self.image_directory)
        #self.guider = Guider(self.camera, self.telescope)
        
        self.filterwheel_dict = filter_wheel.get_filter().filter_position_dict()
        self.config_dict = config_reader.get_config()
        
        self.conditions.start()
        self.camera.start()
        self.telescope.start()
        self.dome.start()
        self.focuser.start()
        self.focus_procedures.start()
        self.flatlamp.start()
        self.calibration.start()
        
    def everything_ok(self):
        if not self.camera.live_connection.wait(timeout = 10):
            check = False
            logging.error('Camera connection timeout')
        elif not self.telescope.live_connection.wait(timeout = 10):
            check = False
            logging.error('Telescope connection timeout')
        elif not self.dome.live_connection.wait(timeout = 10):
            check = False
            logging.error('Dome connection timeout')
        elif not self.focuser.live_connection.wait(timeout = 10):
            check = False
            logging.error('Focuser connection timeout')
        elif self.conditions.weather_alert.isSet():
            self._shutdown_procedure(calibration=True)
            if self.conditions.sun:
                sunset_time = conversion_utils.get_sunset(datetime.datetime.now(self.tz), self.config_dict.site_latitude, self.config_dict.site_longitude)
                logging.info('The Sun has risen above the horizon...observing will stop until the Sun sets again at {}.'.format(sunset_time.strftime('%Y-%m-%d %H:%M:%S%z')))
                time.sleep(60*self.config_dict.min_reopen_time)
                sunset_epoch_milli = time_utils.datetime_to_epoch_milli_converter(sunset_time)
                current_epoch_milli = time_utils.datetime_to_epoch_milli_converter(datetime.datetime.now(self.tz))
                time.sleep((sunset_epoch_milli - current_epoch_milli)/1000)
                logging.info('The Sun should now be setting again...observing will resume shortly.')
                if not self.conditions.weather_alert.isSet():
                    check = True
                    if not self.current_ticket:
                        self.observe()
                    elif self.current_ticket.end_time <= datetime.datetime.now(self.tz):
                        self._startup_procedure()
                        self._ticket_slew(self.current_ticket)
                        self.focus_target(self.current_ticket)
                else: 
                    print('Weather is still too poor to resume observing.')
                    self.everything_ok()
            elif not self.conditions.sun:
                time.sleep(60*self.config_dict.min_reopen_time)
                while self.conditions.weather_alert.isSet():
                    time.sleep(self.config_dict.weather_freq*60)
                if not self.conditions.weather_alert.isSet() and self.current_ticket.end_time <= datetime.datetime.now(self.tz):
                    self._startup_procedure()
                    self._ticket_slew(self.current_ticket)
                    self.focus_target(self.current_ticket)
                    check = True
        else:
            check = True
        return check

    def _startup_procedure(self, calibration=False):
        Initial_check = self.everything_ok()
        
        self.camera.onThread(self.camera.coolerSet, True)
        self.dome.onThread(self.dome.ShutterPosition)
        time.sleep(2)
        if calibration:
            self.camera.cooler_settle.wait()
            print('Taking darks and flats...')
            self.take_calibration_images(beginning=True)
        Initial_shutter = self.dome.shutter
        if Initial_shutter in (1,3,4) and Initial_check == True:
            self.dome.onThread(self.dome.MoveShutter, 'open')
            self.dome.onThread(self.dome.Home)
            self.telescope.onThread(self.telescope.Unpark)
        elif not Initial_check:
            self.shutdown(); return
        self.camera.onThread(self.camera.cooler_ready)
        self.dome.onThread(self.dome.SlaveDometoScope, True)
        return Initial_shutter
    
    def _ticket_slew(self, ticket):
        self.telescope.onThread(self.telescope.Slew, ticket.ra, ticket.dec)
        slew = self.telescope.slew_done.wait(timeout = 60*2)
        if not slew:
            logging.error('Telescope slew has failed.  Retrying...')
            self.telescope.onThread(self.telescope.Slew, ticket.ra, ticket.dec)
            slew2 = self.telescope.slew_done.wait(timeout = 60*2)
            if not slew2:
                logging.critical('Telescope still cannot slew to target.  Cannot continue observing.')
                return False
        return True

    def observe(self):
        Initial_shutter = self._startup_procedure()
        
        for ticket in self.observation_request_list:
            self.current_ticket = ticket
            if not self.everything_ok(): 
                self.shutdown(); return
            self.crash_check('TheSkyX.exe')
            self.crash_check('ASCOMDome.exe')
            if not self._ticket_slew(ticket):
                return
            if Initial_shutter in (1,3,4):
                self.dome.move_done.wait()
                self.dome.shutter_done.wait()
            self.camera.cooler_settle.wait()
            self.FWHM = self.focus_target(ticket)
            
            self.tz = ticket.start_time.tzinfo
            current_time = datetime.datetime.now(self.tz)
            if ticket.start_time > current_time:
                print("It is not the start time {} of {} observation, "
                      "waiting till start time.".format(ticket.start_time.isoformat(), ticket.name))
                current_epoch_milli = time_utils.datetime_to_epoch_milli_converter(current_time)
                start_time_epoch_milli = time_utils.datetime_to_epoch_milli_converter(ticket.start_time)
                time.sleep((start_time_epoch_milli - current_epoch_milli)/1000)
    
            if not self.everything_ok(): 
                self.shutdown(); return
            
            input("The program is ready to start taking images of {}.  Please take this time to "
                  "check the focus and pointing of the target.  When you are ready, press Enter: ".format(ticket.name))
            (taken, total) = self.run_ticket(ticket)
            print("{} out of {} exposures were taken for {}.  Moving on to next target.".format(taken, total, ticket.name))
        
        if self.config_dict.calibration_time == "end":
            calibration = True
        else:
            calibration = False
        self.shutdown(calibration)
        
    def focus_target(self, ticket):
        if type(ticket.filter) is list:
            focus_filter = [ticket.filter[0]]
        elif type(ticket.filter) is str:
            focus_filter = ticket.filter
        focus_exposure = int(self.config_dict.focus_exposure_multiplier*ticket.exp_time)
        if focus_exposure <= 0: 
            focus_exposure = 1
        FWHM = self.focus_procedures.onThread(self.focus_procedures.StartupFocusProcedure, focus_exposure, self.filterwheel_dict[focus_filter], 
                                              self.image_directory)
        while not self.focus_procedures.focused.isSet():
            self.crash_check('RoboFocus.exe')
            time.sleep(10)
        return FWHM
        
    def run_ticket(self, ticket):
        self.focus_procedures.onThread(self.focus_procedures.ConstantFocusProcedure, self.FWHM, self.image_directory)
        
        if ticket.cycle_filter:
            img_count = self.take_images(ticket.name, ticket.num, ticket.exp_time,
                                         ticket.filter, ticket.end_time, self.image_directory,
                                         True)
            self.focus_procedures.onThread(self.focus_procedures.StopConstantFocusing)
            return (img_count, ticket.num)
        
        else:
            img_count = 0
            for i in range(len(ticket.filter)):
                img_count_filter = self.take_images(ticket.name, ticket.num, ticket.exp_time,
                                             [ticket.filter[i]], ticket.end_time, self.image_directory,
                                             False)
                img_count += img_count_filter
            self.focus_procedures.onThread(self.focus_procedures.StopConstantFocusing)
            return (img_count, ticket.num*len(ticket.filter))

    def take_images(self, name, num, exp_time, filter, end_time, path, cycle_filter):
        num_filters = len(filter)
        image_num = 1
        N = []
        image_base = {}
        i = 0
        while i < num:
            logging.debug('In take_images loop')
            if end_time <= datetime.datetime.now(self.tz):
                print("The observations end time of {} has passed.  "
                      "Stopping observation of {}.".format(end_time, name))
                break
            if not self.everything_ok(): break
            current_filter = filter[i % num_filters]
            image_name = "{0:s}_{1:d}s_{2:s}-{3:04d}.fits".format(name, exp_time, current_filter, image_num)
            
            if i == 0 and os.path.exists(os.path.join(path, image_name)):   #Checks if images already exist (in the event of a crash)
                for f in filter:
                    N = [0]    
                    for fname in os.listdir(path):
                        n = re.search('{0:s}_{1:d}s_{2:s}-(.+?).fits'.format(name, exp_time, f), fname)
                        if n: N.append(int(n.group(1)))
                    image_base[f] = max(N) + 1
                
                image_name = "{0:s}_{1:d}s_{2:s}-{3:04d}.fits".format(name, exp_time, current_filter, image_base[current_filter])
                
            self.camera.onThread(self.camera.expose, 
                                 int(exp_time), self.filterwheel_dict[current_filter], os.path.join(path, image_name), "light")
            self.camera.image_done.wait(timeout = exp_time*2 + 60)
            
            if self.crash_check('MaxIm_DL.exe'):
                continue
            if self.crash_check('RoboFocus.exe'):
                pass
            
            if cycle_filter:
                if N:
                    image_num = math.floor(image_base[filter[(i + 1) % num_filters]] + ((i + 1)/num_filters))
                else:
                    image_num = math.floor(1 + ((i + 1)/num_filters))
            elif not cycle_filter:
                if N:
                    image_num = image_base[filter[(i + 1) % num_filters]] + (i + 1)
                else:
                    image_num += 1
            i += 1
        return i
    
    def crash_check(self, program):
        cmd = 'tasklist /FI "IMAGENAME eq %s" /FI "STATUS eq running"' % program
        status = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
        responding = program in str(status)
            
        if not responding:
            prog_dict = {'MaxIm_DL.exe': [self.camera, Camera], 'TheSkyX.exe': [self.telescope, Telescope],
                         'ASCOMDome.exe': [self.dome, Dome], 'RoboFocus.exe': [self.focuser, Focuser]}
            prog_dict[program][0].crashed.set()
            logging.error('{} is not responding.  Restarting...'.format(program))
            time.sleep(5)
            prog_dict[program][0].crashed.clear()
            subprocess.call('taskkill /f /im {}'.format(program))                      #TODO: Maybe add check if os = windows?
            time.sleep(5)
            prog_dict[program][0] = prog_dict[program][1]()                             #TODO: Restart FocusProcedures & Guider too if cam/focus/telescope crashes
            prog_dict[program][0].start()
            time.sleep(5)
            if program in ('MaxIm_DL.exe', 'RoboFocus.exe'):
                time.sleep(5)
                self.focus_procedures = FocusProcedures(self.focuser, self.camera)
                self.focus_procedures.start()
                time.sleep(5)
                self.focus_procedures.onThread(self.focus_procedures.ConstantFocusProcedure(self.FWHM, self.image_directory))
            return True
        else:
            return False
        
    def take_calibration_images(self, beginning=False):
        for i in range(len(self.observation_request_list)):
            if self.calibrated_tickets[i]:
                continue
            self.calibration.onThread(self.calibration.take_flats, self.observation_request_list[i])
            self.calibration.calibration_done.wait()
            self.calibration.onThread(self.calibration.take_darks, self.observation_request_list[i])
            self.calibration.calibration_done.wait()
            self.calibrated_tickets[i] = 1
            if self.current_ticket == self.observation_request_list[i] and beginning == False:
                break
    
    def shutdown(self, calibration=False):
        if self.shutdown_toggle or self.conditions.weather_alert.isSet():
            self._shutdown_procedure(calibration=calibration)
            self.stop_threads()
        else:
            pass
        
    def stop_threads(self):
        self.camera.onThread(self.camera.disconnect)
        self.telescope.onThread(self.telescope.disconnect)
        self.dome.onThread(self.dome.disconnect)
        self.focuser.onThread(self.focuser.disconnect)
        self.flatlamp.onThread(self.flatlamp.disconnect)
        
        self.conditions.stop.set()
        self.camera.onThread(self.camera.stop)
        self.telescope.onThread(self.telescope.stop)
        self.dome.onThread(self.dome.stop)
        self.focuser.onThread(self.focuser.stop)
        self.focus_procedures.onThread(self.focus_procedures.stop)
        self.flatlamp.onThread(self.flatlamp.stop)
    
    def _shutdown_procedure(self, calibration):
        print("Shutting down observatory.")
        self.dome.onThread(self.dome.SlaveDometoScope, False)
        self.telescope.onThread(self.telescope.Park)
        self.dome.onThread(self.dome.Park)
        self.dome.onThread(self.dome.MoveShutter, 'close')
        if calibration:
            print('Taking flats and darks...')
            self.take_calibration_images()
        
        self.camera.onThread(self.camera.coolerSet, False)
        self.telescope.slew_done.wait()
        self.dome.move_done.wait()
        self.dome.shutter_done.wait()