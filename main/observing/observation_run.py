import datetime
import time
import os
import math
import re
import logging
import threading

from ..common.util import time_utils
from ..common.IO import config_reader
from ..common.datatype import filter_wheel
from ..controller.camera import Camera
from ..controller.telescope import Telescope
from ..controller.dome import Dome
from ..controller.focuser import Focuser
#from .guider import Guider
from .weather_checker import Weather
    
class ObservationRun():
    def __init__(self, observation_request_list, image_directory):
        '''

        :param observation_request_list: List of ObservationTickets
        '''
        self.image_directory = image_directory
        self.observation_request_list = observation_request_list
        self.camera = Camera()
        self.telescope = Telescope()
        self.dome = Dome()
        self.weather = Weather()
        self.focuser = Focuser(self.camera)
        #self.guider = Guider(self.camera, self.telescope)
        
        self.filterwheel_dict = filter_wheel.get_filter().filter_position_dict()
        self.config_dict = config_reader.get_config()
        
    def check_weather(self):
        if self.weather.weather_alert.isSet():
            return True
        else:
            return False

    def observe(self):
        Initial_weather = self.check_weather()
        self.weather.start()
        self.camera.start()
        self.telescope.start()
        self.dome.start()
        self.focuser.start()
        
        self.dome.live_connection.wait()
        self.dome.onThread(self.dome.ShutterPosition)
        time.sleep(1)
        Initial_shutter = self.dome.shutter
        if Initial_shutter in (1,3,4) and Initial_weather == False:
            self.dome.onThread(self.dome.MoveShutter, 'open')
            self.dome.onThread(self.dome.Home)
            self.telescope.onThread(self.telescope.Unpark)
        elif Initial_weather:
            self.shutdown(); return
        self.camera.onThread(self.camera.cooler_ready)
        self.dome.onThread(self.dome.SlaveDometoScope, True)
        
        for ticket in self.observation_request_list:
            if self.check_weather(): 
                self.shutdown(); return
            self.telescope.onThread(self.telescope.Slew, ticket.ra, ticket.dec)
            self.telescope.slew_done.wait()
            if Initial_shutter in (1,3,4):
                self.dome.move_done.wait()
                self.dome.shutter_done.wait()
            self.tz = ticket.start_time.tzinfo
            current_time = datetime.datetime.now(self.tz)
            '''
            current_time_local = datetime.datetime.now()
            # Maybe calculate sunrise/sunset times on daily basis?
            if current_time_local.month >= 3 and current_time_local.month <= 8:     # Between March and August (Spring - Summer)
                sunrise = 5
                sunset = 20
            else:   # Between September and February (Fall - Winter)
                sunrise = 7
                sunset = 17
            if current_time_local.hour > sunrise and current_time_local < sunset:
                print("It has become too bright for observations for tonight--the Sun is rising."
                      "Stopping observations until the next night.")
                self._shutdown_procedure()
                
                time.sleep(x)
                reconnect and restart everything (maybe make that into a different function, or just move this above the other stuff)
            '''
            
            if ticket.start_time > current_time:
                print("It is not the start time {} of {} observation, "
                      "waiting till start time.".format(ticket.start_time.isoformat(), ticket.name))
                current_epoch_milli = time_utils.datetime_to_epoch_milli_converter(current_time)
                start_time_epoch_milli = time_utils.datetime_to_epoch_milli_converter(ticket.start_time)
                time.sleep((start_time_epoch_milli - current_epoch_milli)/1000)
            
            self.camera.cooler_settle.wait()
            if self.check_weather(): 
                self.shutdown(); return
            # self.focus_target(ticket)
            input("The program is ready to start taking images of {}.  Please take this time to "
                  "check the focus and pointing of the target.  When you are ready, press Enter: ".format(ticket.name))
            (taken, total) = self.run_ticket(ticket)
            print("{} out of {} exposures were taken for {}.  Moving on to next target.".format(taken, total, ticket.name))
        self.shutdown()
        
    def focus_target(self, ticket):
        if type(ticket.filter) is list:
            focus_filter = [ticket.filter[0]]
        elif type(ticket.filter) is str:
            focus_filter = ticket.filter
        focus_exposure = int(self.config_dict.focus_exposure_multiplier*ticket.exp_time)
        if focus_exposure <= 0: focus_exposure = 1
        self.focuser.onThread(self.focuser.AutoFocusProcedure,
                              focus_exposure, self.filterwheel_dict[focus_filter], self.config_dict.initial_focus_delta,
                              self.config_dict.focus_iterations, self.image_directory, self.config_dict.focus_goal)
        self.focuser.focused.wait()
        return
        
    def run_ticket(self, ticket):
        if ticket.cycle_filter:
            img_count = self.take_images(ticket.name, ticket.num, ticket.exp_time,
                                         ticket.filter, ticket.end_time, self.image_directory,
                                         True)
            return (img_count, ticket.num)
        
        else:
            img_count = 0
            for i in range(len(ticket.filter)):
                img_count_filter = self.take_images(ticket.name, ticket.num, ticket.exp_time,
                                             [ticket.filter[i]], ticket.end_time, self.image_directory,
                                             False)
                img_count += img_count_filter
            return (img_count, ticket.num*len(ticket.filter))

    def take_images(self, name, num, exp_time, filter, end_time, path, cycle_filter):
        num_filters = len(filter)
        image_num = 1
        N = []
        image_base = {}
        images_taken = 0
        for i in range(num):
            logging.debug('In take_images loop')
            if end_time <= datetime.datetime.now(self.tz):
                print("The observations end time of {} has passed.  "
                      "Stopping observation of {}.".format(end_time, name))
                break
            if self.check_weather(): break
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
            self.camera.image_done.wait()
            # Guider here
            
            images_taken += 1
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
        return images_taken
    
    def shutdown(self):
        timeout = 60
        t = threading.Timer(timeout, self._shutdown_procedure)
        t.start()
        response = input("The last observation ticket has finished.  Shut down? (y/n): ")
        if response == 'y':
            t.cancel()
            self._shutdown_procedure()
        elif response == 'n':
            t.cancel()
            self.stop_threads()
            return
        
    def stop_threads(self):
        self.weather.stop.set()
        self.camera.onThread(self.camera.stop)
        self.telescope.onThread(self.telescope.stop)
        self.dome.onThread(self.dome.stop)
        self.focuser.onThread(self.focuser.stop)
    
    def _shutdown_procedure(self):
        print("Shutting down observatory.")
        self.dome.onThread(self.dome.SlaveDometoScope, False)
        self.telescope.onThread(self.telescope.Park)
        self.dome.onThread(self.dome.Park)
        self.dome.onThread(self.dome.MoveShutter, 'close')
        
        self.telescope.slew_done.wait()
        self.dome.move_done.wait()
        self.dome.shutter_done.wait()
        self.camera.onThread(self.camera.disconnect)
        self.telescope.onThread(self.telescope.disconnect)
        self.dome.onThread(self.dome.disconnect)
        self.focuser.onThread(self.focuser.disconnect)
        
        self.stop_threads()

        