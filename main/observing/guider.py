import threading
import logging
import os
import numpy as np

from ..controller.hardware import Hardware
from ..common.IO import config_reader
from ..common.util import filereader_utils


class Guider(Hardware):
    
    def __init__(self, camera_obj, telescope_obj):
        """
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

        """
        self.camera = camera_obj
        self.telescope = telescope_obj
        self.config_dict = config_reader.get_config()
        self.guiding = threading.Event()
        self.loop_done = threading.Event()

        super(Guider, self).__init__(name='Guider')

    def _class_connect(self):
        """
        Description
        -----------
        Overwrites base not implemented method.  However, nothing is necessary for the guider specifically,
        so the method just passes.

        Returns
        -------
        True : BOOL
        """
        return True
                
    def find_guide_star(self, path, subframe=None):
        """
        Description
        -----------
        Finds the brightest unsaturated star in an image to be used as a guiding star.  If there is a subframe, it
        will instead try to find the star closest to the center of the subframe.

        Parameters
        ----------
        path : STR
            Path to image file used to find guide star.
        subframe : TUPLE, optional
            x and y coordinate of star to set a subframe around. The default is None, which will scan the
            entire image.

        Returns
        -------
        guider_star : TUPLE
            Tuple with x-coordinate and y-coordinate of the star in the image.

        """
        stars, peaks = filereader_utils.findstars(path, self.config_dict.saturation, subframe=subframe)
        guider_star = None
        if not subframe:
            i = 1
            j = 0
            while i < len(stars) - 1 - j:
                dist_next = np.sqrt((stars[i][0] - stars[i + 1][0]) ** 2 + (stars[i][1] - stars[i + 1][1]) ** 2)
                dist_prev = np.sqrt((stars[i][0] - stars[i - 1][0]) ** 2 + (stars[i][1] - stars[i - 1][1]) ** 2)
                if peaks[i] >= self.config_dict.saturation or dist_next < 100 or dist_prev < 100:
                    peaks.pop(i)
                    stars.pop(i)
                    j += 1
                else:
                    i += 1
            if len(peaks) >= 3:
                maxindex = peaks.index(max(peaks[1:len(peaks)-1]))
                guider_star = stars[maxindex]
            else:
                guider_star = None
        else:
            minsep = 1000
            minstar = None
            r = self.config_dict.guider_max_move / self.config_dict.plate_scale * 1.5
            for star in stars:
                distance = np.sqrt((star[0]-r)**2 + (star[1]-r)**2)
                if distance < minsep:
                    minsep = distance
                    minstar = star
            guider_star = minstar
        return guider_star

    @staticmethod
    def find_newest_image(image_path):
        """
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

        """
        images = os.listdir(image_path)
        paths = [full_path for fname in images if os.path.isfile(full_path := os.path.join(image_path, fname))]
        newest_image = max(paths, key=os.path.getctime)
        return newest_image
    
    def guiding_procedure(self, image_path):
        """
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

        """
        self.guiding.set()
        x_initial = 0
        y_initial = 0
        while self.guiding.isSet():
            self.camera.image_done.wait()
            newest_image = self.find_newest_image(image_path)
            star = self.find_guide_star(newest_image)
            if not star:
                logging.warning('Guider could not find a suitable guide star...waiting for next image to try again.')
            else:
                x_initial = star[0]
                y_initial = star[1]
                break
        failures = 0
        while self.guiding.isSet():
            self.camera.image_done.wait(timeout=30*60)
            self.loop_done.clear()
            newest_image = self.find_newest_image(image_path)
            subframe = None if failures >= 3 else (x_initial, y_initial)
            star = self.find_guide_star(newest_image, subframe=subframe)
            if not star:
                logging.warning('Guider could not find a suitable guide star...waiting for next image to try again.')
                failures += 1
                continue
            elif failures >= 3:
                failures = 0
                x_initial = star[0]
                y_initial = star[1]
                logging.info('Guider has selected a new guide star.  Continuing to guide.')
                continue
            failures = 0
            x_0 = y_0 = self.config_dict.guider_max_move / self.config_dict.plate_scale * 1.5
            x = star[0]
            y = star[1]
            logging.debug('Guide star relative coordinates: x={}, y={}'.format(x, y))
            logging.debug('Guide star absolute coordinates: x={}, y={}'.format(x_initial, y_initial))
            separation = np.sqrt((x - x_0)**2 + (y - y_0)**2)
            if separation >= self.config_dict.guiding_threshold:
                xdistance = x - x_0
                ydistance = y - y_0
                if xdistance == 0:
                    if ydistance > 0:
                        angle = (1/2)*np.pi
                    else:
                        angle = (-1/2)*np.pi
                else:
                    angle = np.arctan(ydistance/xdistance)
                    if xdistance < 0:
                        angle += np.pi

                deltangle = angle - self.config_dict.guider_angle
                # Assumes guider angle (angle b/w RA/Dec axes and Image X/Y axes) is constant
                if ((-1/2)*np.pi <= deltangle <= (1/2)*np.pi) or ((3/2)*np.pi <= deltangle <= 2*np.pi):
                    xdirection = 'right'
                else:
                    xdirection = 'left'
                if 0 <= deltangle <= np.pi:
                    ydirection = 'down'
                else:
                    ydirection = 'up'
                xjog_distance = abs(separation * np.cos(deltangle)) * self.config_dict.plate_scale * \
                    self.config_dict.guider_ra_dampening
                yjog_distance = abs(separation * np.sin(deltangle)) * self.config_dict.plate_scale * \
                    self.config_dict.guider_dec_dampening
                jog_separation = np.sqrt(xjog_distance**2 + yjog_distance**2)
                if jog_separation >= self.config_dict.guider_max_move:
                    logging.warning('Guide star has moved substantially between images...If the telescope did not move '
                                    'suddenly, the guide star most likely has become saturated and the guider has '
                                    'picked a new star.')
                    # Changes initial absolute coordinates to match the "new" guide star
                    new_star = self.find_guide_star(newest_image)
                    x_initial = new_star[0]
                    y_initial = new_star[1]
                elif jog_separation < self.config_dict.guider_max_move:
                    logging.debug('Guider is making an adjustment')
                    logging.debug('xdistance: {}\"; ydistance: {}\"'.format(xjog_distance, yjog_distance))
                    logging.debug('Delta Angle: {} rad'.format(deltangle))
                    logging.debug('Separation: {} px'.format(separation))
                    logging.debug('Move Direction: {} {}'.format(xdirection, ydirection))
                    logging.debug('Plate Scale: {}\"/px'.format(self.config_dict.plate_scale))
                    logging.debug('RA Dampening: {}x'.format(self.config_dict.guider_ra_dampening))
                    logging.debug('Dec Dampening: {}x\n'.format(self.config_dict.guider_dec_dampening))
                    self.telescope.onThread(self.telescope.jog, xdirection, xjog_distance)
                    self.telescope.slew_done.wait()
                    self.telescope.onThread(self.telescope.jog, ydirection, yjog_distance)
                    self.telescope.slew_done.wait()
            self.loop_done.set()

    def stop_guiding(self):
        """
        Description
        -----------
        Stops the GuidingProcedure from running.
        Must NOT be called with onThread, otherwise the guider will be stuck in constant guiding and won't ever
        get to execute stop.

        Returns
        -------
        None.

        """
        self.guiding.clear()
