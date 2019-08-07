import datetime
import time
import os

from main.common.util import time_utils
from main.controller.camera import Camera
from main.common.datatype import filter_wheel

class ObservationRun():

    def __init__(self, observation_request_list, image_directory):
        '''

        :param observation_request_list: List of ObservationTickets
        '''
        self.image_directory = image_directory
        self.observation_request_list = observation_request_list
        self.filterwheel_dict = filter_wheel.get_filter().filter_position_dict()
        self.camera = Camera()


    def observe(self):
        
        for ticket in self.observation_request_list:
            #TODO: slew to RA Dec
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
                             ticket.filter, ticket.end_time, self.image_directory)
            return

        for i in range(len(ticket.filter)):
            self.take_images(ticket.name, ticket.num, ticket.exp_time,
                             list(ticket.filter[i]), ticket.end_time, self.image_directory)


    def take_images(self, name, num, exp_time, filter, end_time, path):
        num_filters = len(filter)

        for i in range(num):
            if end_time <= datetime.datetime.now():
                print("The observations end time of {} has passed.  "
                      "Stopping observation of {}.".format(end_time, name))

            current_filter = filter[num_filters % i]
            image_name = "{}_{}_{}_{}.fits".format(name, current_filter, exp_time, datetime.datetime.now().isoformat())
            self.camera.expose(int(exp_time), self.filterwheel_dict[current_filter], os.path.join(path, image_name))