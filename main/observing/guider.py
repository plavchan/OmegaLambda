import threading
import logging
import os

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
                
    def FindGuideStar(self, path, subframe=None):
        '''
        Description
        -----------
        Finds the brightest unsaturated star in an image to be used as a guiding star.

        Parameters
        ----------
        path : STR
            Path to image file used to find guide star.
        subframe : TUPLE, optional
            x and y coordinate of star to set a subframe around. The default is None, which will scan the
            entire image.

        Returns
        -------
        brightest_unsaturated_star : TUPLE
            Tuple with x-coordinate and y-coordinate of the star in the image.

        '''
        stars, peaks = filereader_utils.FindStars(path, self.config_dict.saturation, subframe=subframe)
        i = 0
        j = 0
        while i < len(stars) - j:
            if peaks[i] >= self.config_dict.saturation:
                peaks.pop(i)
                stars.pop(i)
                j += 1
            i += 1
        maxindex = peaks.index(max(peaks))
        brightest_unsaturated_star = stars[maxindex]
        #TODO: insert backup star in case guide star gets above 20,000 counts over the night
        return brightest_unsaturated_star
    
    
    
    @staticmethod
    def FindNewestImage(image_path):
        '''
        Description
        -----------
        Finds the newest created file in a folder

        Parameters
        ----------
        image_path : STR
            Path to the folder of files.

        Returns
        -------
        newest_image : STR
            Path to the newest created file in that folder.

        '''
        images = os.listdir(image_path)
        paths = []
        for fname in images:
            full_path = os.path.join(image_path, fname)
            if os.path.isfile(full_path): paths.append(full_path)
            else: continue
        newest_image = max(paths, key=os.path.getctime)
        return newest_image
    
    def GuidingProcedure(self, image_path):
        '''
        Description
        -----------
        The guiding procedure.  Finds the guide star after each new image and pulse guides the telescope
        if the star has moved too far.

        Parameters
        ----------
        image_path : STR
            Path to the folder where images are saved.

        Returns
        -------
        None.

        '''
        self.guiding.set()
        self.camera.image_done.wait()
        newest_image = self.FindNewestImage(image_path)
        star = self.FindGuideStar(newest_image)
        x_0 = star[0]
        y_0 = star[1]
        large_move_recovery_x = 0; large_move_recovery_y = 0
        while self.guiding.isSet():
            self.camera.image_done.wait()
            newest_image = self.FindNewestImage(image_path)
            star = self.FindGuideStar(newest_image, subframe=(x_0, y_0))
            x = star[0]
            y = star[1]
            if abs(x - x_0) >= self.config_dict.guiding_threshold:
                xdistance = x - x_0
                if xdistance >= 0: direction = 'right'  # Star has moved right in the image, so we want to move it back left, meaning we need to move the telescope right
                elif xdistance < 0: direction = 'left'  # Star has moved left in the image, so we want to move it back right, meaning we need to move the telescope left
                jog_distance = abs(xdistance)*self.config_dict.plate_scale*self.config_dict.guider_ra_dampening
                if jog_distance >= self.config_dict.guider_max_move:
                    large_move_recovery_x += 1
                    logging.warning('Guide star has moved substantially between images...If the telescope did not move suddenly, there may'
                                    'be an issue with the FindGuideStar algorithm.')
                if jog_distance < self.config_dict.guider_max_move or large_move_recovery_x >= 5:
                    logging.debug('Guider is making an adjustment in RA')
                    self.telescope.onThread(self.telescope.Jog, direction, jog_distance)
                    self.telescope.slew_done.wait()
                    large_move_recovery_x = 0
            if abs(y - y_0) >= self.config_dict.guiding_threshold:
                ydistance = y - y_0
                if ydistance >= 0: direction = 'up'   # Star has moved up in the image, so we want to move it back down, meaning we need to move the telescope up
                elif ydistance < 0: direction = 'down' # Star has moved down in the image, so we want to move it back up, meaning we need to move the telescope down
                jog_distance = abs(ydistance)*self.config_dict.plate_scale*self.config_dict.guider_dec_dampening
                if jog_distance >= self.config_dict.guider_max_move:
                    large_move_recovery_y += 1
                    logging.warning('Guide star has moved substantially between images...If the telescope did not move suddenly, there may'
                                    'be an issue with the FindGuideStar algorithm.')
                if jog_distance < self.config_dict.guider_max_move or large_move_recovery_y >= 5:
                    logging.debug('Guider is making an adjustment in Dec')
                    self.telescope.onThread(self.telescope.Jog, direction, jog_distance)
                    self.telescope.slew_done.wait()
                    large_move_recovery_y = 0
                
    def StopGuiding(self):
        '''
        Description
        -----------
        Stops the GuidingProcedure from running.

        Returns
        -------
        None.

        '''
        self.guiding.clear()