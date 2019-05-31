import datetime
import pickle

class ObservationRequest():

    def __init__(self, name, ra, dec, filter, num, exp_time, cycle_filter):
        self.name = name
        self.ra = ra
        self.dec = dec
        self.filter = filter
        self.num = num
        self.exp_time = exp_time
        self.cycle_filter = cycle_filter
        self.start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.end_time = None

    def finish_observation(self):
        self.end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def serialized(self):
        return pickle.dumps(self)