from main.controller.camera import Camera

class ObservationRun():

    def __init__(self, observation_request_list):
        self.observation_request_list = observation_request_list
        self.camera = Camera()

    def observe(self):
        pass