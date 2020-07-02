import threading

from ..controller.hardware import Hardware
from ..common.IO import config_reader
from ..common.util import filereader_utils

'''
1. Camera takes an exposure in observation_run
2. Find & record test star's position in FOV
3. Camera takes another exposure in observation_run
4. Compare test star's new position to its last one
5. If too small, do nothing, keep first position saved (so that when we eventually jog, 
   it is correct for the difference since the first exposure)
6. If big enough, Pulseguide/jog telescope to correct for the difference b/w
   previous (or first) location and current location
7. Make sure dome slaves correctly (should already be taken care of)
'''

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
        
        #Idea would be to wait for the last camera.expose from take_images, then call guider.findstars or something to see if a move is necessary
                
    def FindGuideStar(self, path):  # Remove IRAFStarFinder
        maximum = 0
        data_table = filereader_utils.IRAF_calculations(path)
        for i in range(1, len(data_table['peak'])):
            row = i
            flux = data_table['peak'][row]
            if flux > maximum and flux <= self.config_dict.saturation:
                maximum = flux
                maxrow = row
        brightest_unsaturated_star = data_table[:][maxrow]  # Use this as a guiding star
        return brightest_unsaturated_star
    
    def GuidingProcedure(self, image_path):
        self.guiding.set()
        self.camera.image_done.wait()
        star = self.FindGuideStar(image_path)
        x_0 = star['xcentroid']
        y_0 = star['ycentroid']
        large_move_recovery = 0
        while self.guiding.isSet():
            self.camera.image_done.wait()
            star = self.FindGuideStar(image_path)   # What if we fall behind the camera?
            x = star['xcentroid']
            y = star['ycentroid']
            if abs(x - x_0) >= self.config_dict.guiding_threshold:
                xdistance = x - x_0
                if xdistance >= 0: direction = 'right'  # Star has moved right in the image, so we want to move it back left, meaning we need to move the telescope right
                elif xdistance < 0: direction = 'left'  # Star has moved left in the image, so we want to move it back right, meaning we need to move the telescope left
                jog_distance = abs(xdistance)*self.config_dict.plate_scale*self.config_dict.guider_ra_dampening
                if jog_distance >= self.config_dict.guider_max_move:
                    large_move_recovery += 1
                if jog_distance < self.config_dict.guider_max_move or large_move_recovery >= 6:
                    self.telescope.onThread(self.telescope.Jog, direction, jog_distance)
                    self.telescope.slew_done.wait()
            if abs(y - y_0) >= self.config_dict.guiding_threshold:
                ydistance = y - y_0
                if ydistance >= 0: direction = 'up'   # Star has moved up in the image, so we want to move it back down, meaning we need to move the telescope up
                elif ydistance < 0: direction = 'down' # Star has moved down in the image, so we want to move it back up, meaning we need to move the telescope down
                jog_distance = abs(ydistance)*self.config_dict.plate_scale*self.config_dict.guider_dec_dampening
                if jog_distance >= self.config_dict.guider_max_move:
                    large_move_recovery += 1
                if jog_distance < self.config_dict.guider_max_move or large_move_recovery >= 6:
                    self.telescope.onThread(self.telescope.Jog, direction, jog_distance)
                    self.telescope.slew_done.wait()
                
    def StopGuiding(self):
        self.guiding.clear()