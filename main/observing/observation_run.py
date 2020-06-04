import datetime
import time
import os
import math
import logging

from main.common.util import time_utils
from main.controller.camera import Camera
from main.common.datatype import filter_wheel
from main.common.IO import config_reader
from main.controller.telescope import Telescope
from main.controller.dome import Dome
    
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
        
        self.filterwheel_dict = filter_wheel.get_filter().filter_position_dict()
        self.config_dict = config_reader.get_config()

    def observe(self):
        self.camera.start()
        self.telescope.start()
        self.dome.start()
        
        self.dome.onThread(self.dome.Home)
        self.dome.onThread(self.dome.MoveShutter, 'open')   #Check weather before opening
        self.dome.onThread(self.dome.SlaveDometoScope, True)
        self.telescope.onThread(self.telescope.Unpark)
        self.telescope.Unpark()         #This is weird--not sure why, but the telescope needs to have this on the main thread or else the 
                                        #telescope thread won't do anything.  It jogs it awake or something.
        
        for ticket in self.observation_request_list:
            self.telescope.onThread(self.telescope.Slew, ticket.ra, ticket.dec)
            self.telescope.slew_done.wait()
            self.dome.move_done.wait()
            #self.dome.shutter_done.wait()
            self.tz = ticket.start_time.tzinfo
            current_time = datetime.datetime.now(self.tz)
            if ticket.start_time > current_time:
                print("It is not the start time {} of {} observation, "
                      "waiting till start time.".format(ticket.start_time.isoformat(), ticket.name))
                current_epoch_milli = time_utils.datetime_to_epoch_milli_converter(current_time)
                start_time_epoch_milli = time_utils.datetime_to_epoch_milli_converter(ticket.start_time)
                time.sleep((start_time_epoch_milli - current_epoch_milli)/1000)
            
            #TODO: start guiding
            self.camera.onThread(self.camera.cooler_ready)
            self.camera.cooler_settle.wait()
            input("The program is ready to start taking images of {}.  Please take this time to "
                  "focus and check the pointing of the target.  When you are ready, press Enter: ".format(ticket.name))
            (taken, total) = self.run_ticket(ticket)
            print("{} out of {} exposures were taken for {}.  Moving on to next target.".format(taken, total, ticket.name))
        self.shutdown()
        
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
        n = None
        images_taken = 0
        for i in range(num):
            logging.debug('In take_images loop')
            if end_time <= datetime.datetime.now(self.tz):
                print("The observations end time of {} has passed.  "
                      "Stopping observation of {}.".format(end_time, name))
                break
            
            current_filter = filter[i % num_filters]
            image_name = "{0:s}_{1:d}s_{2:s}-{3:04d}.fits".format(name, exp_time, current_filter, image_num)
            if i == 0 and os.path.exists(os.path.join(path, image_name)):
                n = os.listdir(path)[-1].replace("{0:s}_{1:d}s_{2:s}-".format(name, exp_time, filter[-1]), '').replace('.fits','')
                image_num_base = int(n) + 1
                image_name = "{0:s}_{1:d}s_{2:s}-{3:04d}.fits".format(name, exp_time, current_filter, image_num_base)
            self.camera.onThread(self.camera.expose, 
                                 int(exp_time), self.filterwheel_dict[current_filter], os.path.join(path, image_name), "light")     #Very strange issue where sometimes camera saves 2 images at once (different names)?
            self.camera.image_done.wait()
            images_taken += 1
            if cycle_filter:
                if n:
                    image_num = math.floor(image_num_base + ((i + 1)/num_filters))
                else:
                    image_num = math.floor(1 + ((i + 1)/num_filters))
            elif not cycle_filter:
                image_num += 1
        return images_taken
    
    def shutdown(self):
        print("All targets have finished for tonight.  Shutting down observatory.")
        self.dome.onThread(self.dome.SlaveDometoScope, False)
        self.telescope.onThread(self.telescope.Park)
        self.dome.onThread(self.dome.Park)
        self.dome.onThread(self.dome.MoveShutter, 'close')
        
        self.camera.onThread(self.camera.disconnect)
        self.dome.onThread(self.dome.disconnect)
        self.telescope.onThread(self.telescope.disconnect)
        
        self.camera.onThread(self.camera.stop)
        self.telescope.onThread(self.telescope.stop)
        self.dome.onThread(self.dome.stop)