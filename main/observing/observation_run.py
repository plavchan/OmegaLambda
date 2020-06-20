import datetime
import time
import os
import math
import re
import logging

from main.common.util import time_utils
from main.controller.camera import Camera
from main.common.datatype import filter_wheel
from main.common.IO import config_reader
from main.controller.telescope import Telescope
from main.controller.dome import Dome
from main.observing.weather_checker import Weather
#from main.observing.guider import Guider
    
class ObservationRun():
    def __init__(self, observation_request_list, image_directory):
        '''
        

        Parameters
        ----------
        observation_request_list : LIST
            List of observation tickets.
        image_directory : STR
            Directory to which the images will be saved to.

        Returns
        -------
        None.

        '''

        self.image_directory = image_directory
        self.observation_request_list = observation_request_list
        self.camera = Camera()
        self.telescope = Telescope()
        self.dome = Dome()
        self.weather = Weather()
        #self.guider = Guider(self.camera, self.telescope)
        
        self.filterwheel_dict = filter_wheel.get_filter().filter_position_dict()
        self.config_dict = config_reader.get_config()
        
    def check_weather(self):
        '''
        

        Returns
        -------
        bool
            If True, the weather conditions for observing
            are poor, and so the observing will stop. If False, conditions are 
            good to continiue observation.

        '''
        if self.weather.weather_alert.isSet():
            return True
            
        else:
            return False
                logging.debug('Weather conditions OK for observation')

    def observe(self):
        '''
        
        Desctiption
        ----------
        Makes sure the dome, shutter, camera are ready to begin observation,
        and the start time has passed before beginning observation

        Returns
        -------
        None.

        '''
        self.weather.start()
        time.sleep(5)           #This is needed, or else it checks before weather_checker finishes its first test
        if self.check_weather(): 
            return
        self.camera.start()
        self.telescope.start()
        self.dome.start()
        self.camera.onThread(self.camera.cooler_ready)
        
        self.dome.live_connection.wait()
        self.dome.onThread(self.dome.ShutterPosition) #If open, status = 0 (False), if closed, status = 1 (True)
        time.sleep(1)
        Initial_shutter = self.dome.shutter
        if Initial_shutter:
            self.dome.onThread(self.dome.MoveShutter, 'open')
            self.dome.onThread(self.dome.Home)
            self.dome.onThread(self.dome.SlaveDometoScope, True)
            self.telescope.onThread(self.telescope.Unpark)
        
        for ticket in self.observation_request_list:
            if self.check_weather(): 
                self.shutdown(); return
            if Initial_shutter:
                self.telescope.onThread(self.telescope.Slew, ticket.ra, ticket.dec)
                self.telescope.slew_done.wait()
                self.dome.move_done.wait()
                self.dome.shutter_done.wait()
            self.tz = ticket.start_time.tzinfo
            current_time = datetime.datetime.now(self.tz)
            if ticket.start_time > current_time:
                print("It is not the start time {} of {} observation, "
                      "waiting till start time.".format(ticket.start_time.isoformat(), ticket.name))
                current_epoch_milli = time_utils.datetime_to_epoch_milli_converter(current_time)
                start_time_epoch_milli = time_utils.datetime_to_epoch_milli_converter(ticket.start_time)
                time.sleep((start_time_epoch_milli - current_epoch_milli)/1000)
            
            self.camera.cooler_settle.wait()
            if self.check_weather(): 
                self.shutdown(); return
            input("The program is ready to start taking images of {}.  Please take this time to "
                  "focus and check the pointing of the target.  When you are ready, press Enter: ".format(ticket.name))
            (taken, total) = self.run_ticket(ticket)
            print("{} out of {} exposures were taken for {}.  Moving on to next target.".format(taken, total, ticket.name))
        print("All targets have finished for tonight.")
        logging.info('All targets completed for the night, proceding to shutdown procedure')
        self.shutdown()
        
    def run_ticket(self, ticket):
        '''
        

        Parameters
        ----------
        ticket : STR
            The observation ticket string with information useful to 
            the observing run.

        Returns
        -------
        img_count: INT
            Number of images taken.
        ticket.num: INT
            The total number of images that are specified on the
            observation ticket.

        '''
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
        '''
        

        Parameters
        ----------
        name : STR
            Name of target to be observed.
        num : INT
            Total number of exposures to be taken during the night.
        exp_time : INT
            The exposure time of each image.
        filter : LIST, STR
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
        images_taken : INT
            The number of images taken so far during the observing run.

        '''
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
                    N = []    
                    for fname in os.listdir(path):
                        n = re.search('{0:s}_{1:d}s_{2:s}-(.+?).fits'.format(name, exp_time, f), fname)
                        if n: N.append(int(n.group(1)))
                    image_base[f] = max(N) + 1
                
                image_name = "{0:s}_{1:d}s_{2:s}-{3:04d}.fits".format(name, exp_time, current_filter, image_base[current_filter])
                
            self.camera.onThread(self.camera.expose, 
                                 int(exp_time), self.filterwheel_dict[current_filter], os.path.join(path, image_name), "light")
            self.camera.image_done.wait()
            #self.guider.onThread(self.guider.FindStars)
            #self.guider.onThread(self.guider.ComparePositions)
            #Do NOT wait for guider functions to finish
            
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
        '''
        Description
        ----------
        Safely shuts down the telescope, camera, and dome

        Returns
        -------
        None.

        '''
        print("Shutting down observatory.")
        logging.debug('In shutdown process')
        self.weather.stop()
        self.dome.onThread(self.dome.SlaveDometoScope, False)
        self.telescope.onThread(self.telescope.Park)
        self.dome.onThread(self.dome.Park)
        self.dome.onThread(self.dome.MoveShutter, 'close')
        
        self.telescope.slew_done.wait()
        self.dome.move_done.wait()
        self.dome.shutter_done.wait()
        self.camera.onThread(self.camera.disconnect)
        self.dome.onThread(self.dome.disconnect)
        self.telescope.onThread(self.telescope.disconnect)  #still doesn't disconnect from TheSkyX

        self.camera.onThread(self.camera.stop)
        self.telescope.onThread(self.telescope.stop)
        self.dome.onThread(self.dome.stop)