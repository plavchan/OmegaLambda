import datetime
import time
import os
import math

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
        
        self.filterwheel_dict = filter_wheel.get_filter().filter_position_dict()
        self.config_dict = config_reader.get_config()
#       self.telescope = Telescope()
#       self.dome = Dome()

    def observe(self):
#       self.dome.Home()
#       self.dome.SlaveDometoScope(True)
#       self.telescope.Unpark()
        
        for ticket in self.observation_request_list:           #Will it always be 1 object per ticket, or could we have multiple objects in a single ticket?
#           self.telescope.Slew(ticket.ra, ticket.dec)
            self.tzinfo = ticket.start_time.tzinfo
            current_time = datetime.datetime.now(self.tzinfo)
            if ticket.start_time > current_time:
                print("It is not the start time {} of {} observation, "
                      "waiting till start time.".format(ticket.start_time.isoformat(), ticket.name))
#               if self.dome.ShutterStatus == 1:            
                    #Check weather before opening shutter
#                   self.dome.MoveShutter('open')
                current_epoch_milli = time_utils.datetime_to_epoch_milli_converter(current_time)
                start_time_epoch_milli = time_utils.datetime_to_epoch_milli_converter(ticket.start_time)
                time.sleep((start_time_epoch_milli - current_epoch_milli)/1000)
            
            #TODO: start guiding
            self.run_ticket(ticket)

    def run_ticket(self, ticket):
        if ticket.cycle_filter:
            last = self.take_images(ticket.name, ticket.num, ticket.exp_time,
                                    ticket.filter, ticket.end_time, self.image_directory,
                                    True)
            self.shutdown(last, ticket.num)
            return
        
        else:
            last = 0
            for i in range(len(ticket.filter)):
                last_f = self.take_images(ticket.name, ticket.num, ticket.exp_time,
                                          [ticket.filter[i]], ticket.end_time, self.image_directory,
                                          False)
                last += last_f
                if last_f != ticket.num:
                    break
            self.shutdown(last, ticket.num*len(ticket.filter))

    def take_images(self, name, num, exp_time, filter, end_time, path, cycle_filter):
        num_filters = len(filter)
    
        image_num = 1
        for i in range(num):
            if end_time <= datetime.datetime.now(self.tzinfo):
                print("The observations end time of {} has passed.  "
                      "Stopping observation of {}.".format(end_time, name))
                last_image = i
                break
            
            current_filter = filter[i % num_filters]
            
            image_name = "{0:s}_{1:d}s_{2:s}-{3:04d}.fits".format(name, exp_time, current_filter, image_num)
            self.camera.expose(int(exp_time), self.filterwheel_dict[current_filter], os.path.join(path, image_name), type="light")
            
            if cycle_filter:
                image_num = math.floor(1 + ((i + 1)/num_filters))
            elif not cycle_filter:
                image_num += 1
            
            t = 1
            while not os.path.exists(os.path.join(path, image_name)):
                time.sleep(1)
                if t >= 10:
                    raise TimeoutError('CCD Image Save Timeout')
                    last_image = i
                    break
                t += 1
            last_image = i + 1
        return last_image
            
    def shutdown(self, image, total):
        print("{} out of {} exposures for tonight have finished.".format(image, total))
        self.camera.disconnect()
        #self.dome.disconnect()
        #self.telescope.disconnect()