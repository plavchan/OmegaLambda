import datetime
import time

import main.common.util.time_utils as tutil
from main.controller.camera import Camera

class ObservationRun():

    def __init__(self, observation_request_list):
        '''

        :param observation_request_list: List of ObservationTickets
        '''
        self.observation_request_list = observation_request_list
        self.camera = Camera()

    def observation_request_validity(self):
        '''
        Check observation tickets for proper time sequence and filters

        :return: Boolean
        '''
        pass

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
            #TODO: WIP
