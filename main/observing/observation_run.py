import datetime
import time
import os

import main.common.datatype.filter_wheel
import main.common.util.time_utils as tutil
from main.controller.camera import Camera

class ObservationRun():

    def __init__(self, observation_request_list, image_directory):
        '''

        :param observation_request_list: List of ObservationTickets
        '''
        self.image_directory = image_directory
        self.observation_request_list = observation_request_list
        self.filterwheel_dict = filter_wheel.get_filter().filter_position_dict()
        self.camera = Camera()

    def compare_current_time(self, comparison, future=True):
        '''
        Compares current time to comparison.

        If future is true:
            Make sure comparison is a later datetime than now
        If future is false:
            Make sure comparison is an earlier datetime than now

        :param comparison: DateTime obj
        :param future: Boolean
        :return: Boolean
        '''
        assert isinstance(comparison, datetime.datetime), "Comparison argument must be a datetime object."
        current_dt = datetime.datetime.now()

        if future and comparison >= current_dt:
            return True

        if not future and comparison <= current_dt:
            return True

        return False
    
    def take_images(num, exp_time, filter, end_time, path):
        num_filters = len(filter)
        
        for i in range(num):
            image_name = "SOMETHING" #TODO: need image nomenclature
            current_filter = filter[num_filters%i]
            self.camera.expose(int(exp_time), self.filterwheel_dict[current_filter], os.path.join(path, image_name))
            #TODO: stop observing if end_time is reached.

    
    def run_ticket(self, ticket, filter=None, cycle=False):
        if cycle:
            take_images(ticket.num, ticket.exp_time, ticket.filter, ticket.end_time, path)
            return
       
        if filter:
            take_images(ticket.num, ticket.exp_time, filter, ticket.end_time, path)
            return
        
        #TODO: if cycle is false?
            


    def observe(self):
        
        for ticket in self.observation_request_list:
            #TODO: slew to RA Dec
            #TODO: start guiding
            if not self.compare_current_time(ticket.start_time, future=False):
                print("It is not ticket's start time {}, "
                      "waiting till start time.".format(ticket.start_time.isoformat()))
                current_epoch_milli = tutil.datetime_to_epoch_milli_converter(datetime.datetime.now)
                start_time_epoch_milli = tutil.datetime_to_epoch_milli_converter(ticket.start_time)
                time.sleep((start_time_epoch_milli - current_epoch_milli)/1000)
                
            run_ticket(self, ticket)
                    
                
