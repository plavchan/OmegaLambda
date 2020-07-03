import threading
import logging

from ..controller.hardware import Hardware
from ..common.IO import config_reader
from ..common.util import filereader_utils

class Guider(Hardware):
    
    def __init__(self, camera_obj, telescope_obj):
        '''
        Description
        ------------
        Initializes the guider, with a camera and telescope.

        Parameters
        ----------
        camera_obj : CLASS INSTANCE OBJECT of Camera
            Described in controller/camera.py.  Used for finding stars in images.
        telescope_obj : CLASS INSTANCE OBJECT of Telescope
            Described in controller/telescope.py.  Used for adjusting the telescsope.

        Returns
        -------
        None.

        '''
        self.camera = camera_obj
        self.telescope = telescope_obj
        self.config_dict = config_reader.get_config()
        self.guiding = threading.Event()
        
        super(Guider, self).__init__(name='Guider')
                
    def FindGuideStar(self, path):  # Remove IRAFStarFinder
        maximum = 0
        stars, peaks = filereader_utils.FindStars(path, self.config_dict.saturation)
        i = 0
        maximum = 0
        for star in stars:
            counts = peaks[i]
            if counts >= maximum and counts <= self.config_dict.saturation:
                maximum = counts
                maxindex = i
            i += 1
        brightest_unsaturated_star = stars[maxindex]
        return brightest_unsaturated_star
    
    def GuidingProcedure(self, image_path):
        self.guiding.set()
        self.camera.image_done.wait()
        star = self.FindGuideStar(image_path)
        x_0 = star[0]
        y_0 = star[1]
        large_move_recovery = 0
        while self.guiding.isSet():
            self.camera.image_done.wait()
            star = self.FindGuideStar(image_path)   # What if we fall behind the camera?
            x = star[0]
            y = star[1]
            if abs(x - x_0) >= self.config_dict.guiding_threshold:
                xdistance = x - x_0
                if xdistance >= 0: direction = 'right'  # Star has moved right in the image, so we want to move it back left, meaning we need to move the telescope right
                elif xdistance < 0: direction = 'left'  # Star has moved left in the image, so we want to move it back right, meaning we need to move the telescope left
                jog_distance = abs(xdistance)*self.config_dict.plate_scale*self.config_dict.guider_ra_dampening
                if jog_distance >= self.config_dict.guider_max_move:
                    large_move_recovery += 1
                    logging.warning('Guide star has moved substantially between images...If the telescope did not move suddenly, there may'
                                    'be an issue with the FindGuideStar algorithm.')
                if jog_distance < self.config_dict.guider_max_move or large_move_recovery >= 6:
                    logging.debug('Guider is making an adjustment in RA')
                    self.telescope.onThread(self.telescope.Jog, direction, jog_distance)
                    self.telescope.slew_done.wait()
                    x_0 = x
            if abs(y - y_0) >= self.config_dict.guiding_threshold:
                ydistance = y - y_0
                if ydistance >= 0: direction = 'up'   # Star has moved up in the image, so we want to move it back down, meaning we need to move the telescope up
                elif ydistance < 0: direction = 'down' # Star has moved down in the image, so we want to move it back up, meaning we need to move the telescope down
                jog_distance = abs(ydistance)*self.config_dict.plate_scale*self.config_dict.guider_dec_dampening
                if jog_distance >= self.config_dict.guider_max_move:
                    large_move_recovery += 1
                    logging.warning('Guide star has moved substantially between images...If the telescope did not move suddenly, there may'
                                    'be an issue with the FindGuideStar algorithm.')
                if jog_distance < self.config_dict.guider_max_move or large_move_recovery >= 6:
                    logging.debug('Guider is making an adjustment in Dec')
                    self.telescope.onThread(self.telescope.Jog, direction, jog_distance)
                    self.telescope.slew_done.wait()
                    y_0 = y
                
    def StopGuiding(self):
        self.guiding.clear()