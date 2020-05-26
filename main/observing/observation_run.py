import datetime
import time
import os
import math

from main.common.util import time_utils
from main.controller import camera
from main.common.datatype import filter_wheel
#from main.controller.telescope import Telescope

class ObservationRun():
    def __init__(self, observation_request_list, image_directory):
        '''

        :param observation_request_list: List of ObservationTickets
        '''
        self.image_directory = image_directory
        self.observation_request_list = observation_request_list
        self.camera = camera.Camera()
        
        self.filterwheel_dict = filter_wheel.get_filter().filter_position_dict()
        #self.telescope = Telescope()

    def observe(self):
        
        for ticket in self.observation_request_list:
            if ticket.ra:
                #self.telescope.telescopemove(ticket.ra, ticket.dec)
                #self.run_ticket(ticket)
                pass
        
            for i in range(len(ticket.ra)):
                #self.telescope.telescopemove(list(ticket.ra[i]), list(ticket.dec[i]))
                pass
            
            
            #TODO: start guiding
            if ticket.start_time > datetime.datetime.now():
                print("It is not the start time {} of {} observation, "
                      "waiting till start time.".format(ticket.start_time.isoformat(), ticket.name))
                current_epoch_milli = time_utils.datetime_to_epoch_milli_converter(datetime.datetime.now)
                start_time_epoch_milli = time_utils.datetime_to_epoch_milli_converter(ticket.start_time)
                time.sleep((start_time_epoch_milli - current_epoch_milli)/1000)
                
            self.run_ticket(ticket)

    def run_ticket(self, ticket):

        if ticket.cycle_filter:
            self.take_images(ticket.name, ticket.num, ticket.exp_time,
                             ticket.filter, ticket.end_time, self.image_directory, True)
            return

        for i in range(len(ticket.filter)):
            self.take_images(ticket.name, ticket.num, ticket.exp_time,
                             [ticket.filter[i]], ticket.end_time, self.image_directory, False)


    def take_images(self, name, num, exp_time, filter, end_time, path, cycle_filter):
        num_filters = len(filter)
    
        image_num = 1
        for i in range(num):
            if end_time <= datetime.datetime.now():
                print("The observations end time of {} has passed.  "
                      "Stopping observation of {}.".format(end_time, name))
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
                    break
                t += 1
            