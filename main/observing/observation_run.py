import datetime
import time
import os
import math
import threading

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
#        self.telescope = Telescope()
#        self.dome = Dome()

    def observe(self):
        
#       self.dome.Home()
#       self.dome.SlaveDometoScope(True)
#       self.telescope.Unpark()
        
        first = True
        darks_flats = False
        for ticket in self.observation_request_list:           #Will it always be 1 object per ticket, or could we have multiple objects in a single ticket?
            
#           self.telescope.Slew(ticket.ra, ticket.dec)
            
            #If enough time before first ticket: Take darks & flats
            if first:
                if ticket.start_time > datetime.datetime.utcnow() and (ticket.start_time - datetime.datetime.utcnow() > datetime.timedelta(minutes=self.config_dict.prep_time)):
                    print("It is not the start time {} of {} observation, "
                          "there is enough time to take darks and flats beforehand.".format(ticket.start_time.isoformat(), ticket.name))
                    self.run_darks_flats()
                    darks_flats = True
                first = False
            #If not, run tickets, then take darks & flats
            if ticket.start_time > datetime.datetime.utcnow() and first == False:
                print("It is not the start time {} of {} observation, "
                      "waiting till start time.".format(ticket.start_time.isoformat(), ticket.name))
#               if self.dome.ShutterStatus == 1:            
                    #Check weather before opening shutter
#                   self.dome.MoveShutter('open')
                current_epoch_milli = time_utils.datetime_to_epoch_milli_converter(datetime.datetime.utcnow)
                start_time_epoch_milli = time_utils.datetime_to_epoch_milli_converter(ticket.start_time)
                time.sleep((start_time_epoch_milli - current_epoch_milli)/1000)
            
            #TODO: start guiding
            self.run_ticket(ticket)
        
        #If we didn't take darks and flats before the first ticket, take the now (after the last one)
        if not darks_flats:
            self.run_darks_flats()
    
    #TODO: Darks and flats procedure
    def run_darks_flats(self):
        #If doing before first target, take dome flats while shutter is still closed.  Then, take darks and open shutter.
        #If doing after last target, start closing shutter and take darks first.  Then once closed, take flats.
        pass

    def run_ticket(self, ticket):
    #TODO: Implement threading here
    #TODO: For some reason, threading creates an Attribute error when calling any camera method...
        if ticket.cycle_filter:
            '''
            image_thread = threading.Thread(target=self.take_images, args=(ticket.name, ticket.num, ticket.exp_time,
                                                                           ticket.filter, ticket.end_time, self.image_directory,
                                                                           True))
            image_thread.start()
            '''
            self.take_images(ticket.name, ticket.num, ticket.exp_time,
                             ticket.filter, ticket.end_time, self.image_directory,
                             True)
            return

        for i in range(len(ticket.filter)):
            '''
            image_thread = threading.Thread(target=self.take_images, args=(ticket.name, ticket.num, ticket.exp_time,
                                                                           [ticket.filter[i]], ticket.end_time, self.image_directory,
                                                                           False))
            image_thread.start()
            image_thread.join()     #We don't want multiple image threads going at once in different filters, since that would end up acting like a cycle_filter = True
            '''
            self.take_images(ticket.name, ticket.num, ticket.exp_time,
                             [ticket.filter[i]], ticket.end_time, self.image_directory,
                             False)

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
            
            if i == (num - 1):
                print("All exposures for tonight have finished.  Stopping observations of {}.".format(name))
                
        self.shutdown(name)
            
    def shutdown(self, name):
        self.camera.coolerSet(self.config_dict.cooler_idle_setpoint)
        self.camera.disconnect()