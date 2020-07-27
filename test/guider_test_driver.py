from ..main.common.util import filereader_utils
import matplotlib.pyplot as plt
import photutils
import numpy as np
from ..main.controller.telescope import Telescope
from ..main.common.IO.json_reader import Reader
from ..main.common.datatype.object_reader import ObjectReader
import time


def find_guide_star(path, iteration, subframe=None):
    """
    Description
    -----------
    Finds the brightest unsaturated star in an image to be used as a guiding star.

    Parameters
    ----------
    path : STR
        Path to image file used to find guide star.
    iteration : INT
        Which image iteration you are on (for plotting purposes).
    subframe : TUPLE, optional
        x and y coordinate of star to set a subframe around. The default is None, which will scan the
        entire image.

    Returns
    -------
    brightest_unsaturated_star : TUPLE
        Tuple with x-coordinate and y-coordinate of the star in the image.

    """
    stars, peaks, data, stdev = filereader_utils.findstars(path, 20000, subframe=subframe, return_data=True)
    if not subframe:
        i = 1
        j = 0
        while i < len(stars) - 1 - j:
            dist_next = np.sqrt((stars[i][0] - stars[i+1][0])**2 + (stars[i][1] - stars[i+1][1])**2)
            dist_prev = np.sqrt((stars[i][0] - stars[i-1][0])**2 + (stars[i][1] - stars[i-1][1])**2)
            if peaks[i] >= 20000 or dist_next < 100 or dist_prev < 100:
                peaks.pop(i)
                stars.pop(i)
                j += 1
            i += 1
        if len(peaks) >= 3:
            maxindex = peaks.index(max(peaks[1:len(peaks)-1]))
            guider_star = stars[maxindex]
        else:
            guider_star = None
    else:
        minsep = 1000
        minstar = None
        for star in stars:
            distance = np.sqrt((star[0] - 250) ** 2 + (star[1] - 250) ** 2)
            if distance < minsep:
                minsep = distance
                minstar = star
        if minstar:
            guider_star = minstar
        else:
            guider_star = None
    plt.figure()
    plt.imshow(data, cmap='YlGn')
    apertures = photutils.CircularAperture(guider_star, r=6)
    apertures.plot(color='blue', lw=1.5, alpha=0.5)
    plt.savefig(r'C:/Users/GMU Observtory1/-omegalambda/test/guider_test_plot-{}.png'.format(iteration))
    plt.close()
    return guider_star


def guide_test_func():

    star = find_guide_star(
        r'H:\Observatory Files\Observing Sessions\2020_Data\20200726\HIP-xxxxGuidertest_15s_r-0019.fits', 1
    )
    x_initial = star[0]
    y_initial = star[1]
    i = 0
    while i < 10:
        moved = False
        star = find_guide_star(
            r'H:\Observatory Files\Observing Sessions\2020_Data\20200726\HIP-xxxxGuidertest_15s_r-{0:04d}.fits'.format(18 - i),
            iteration=i+2, subframe=(x_initial, y_initial))
        x_0 = 250
        y_0 = 250
        x = star[0]
        y = star[1]
        print('Image number: {0:04d}'.format(18 - i))
        print('Initial coordinates: x={}, y={}'.format(x_initial, y_initial))
        print('Guide star relative coordinates: x={}, y={}'.format(x, y))
        separation = np.sqrt((x - x_0) ** 2 + (y - y_0) ** 2)
        if separation >= 30.0:
            xdistance = x - x_0
            ydistance = y - y_0
            if xdistance == 0:
                if ydistance > 0:
                    angle = (1/2)*np.pi
                else:
                    angle = (-1/2)*np.pi
            else:
                angle = np.arctan(ydistance / xdistance)
                if xdistance < 0:
                    angle += np.pi
            guideangle = 0
            deltangle = angle - guideangle
            xdirection = None
            if (-np.pi/2 <= deltangle <= np.pi/2) or ((3/2)*np.pi <= deltangle <= 2*np.pi):
                xdirection = 'right'
            # Star has moved right in the image, so we want to move it back left,
            # meaning we need to move the telescope right
            else:
                xdirection = 'left'
            # Star has moved left in the image, so we want to move it back right,
            # meaning we need to move the telescope left
            ydirection = None
            if 0 <= deltangle <= np.pi:
                ydirection = 'up'
            # Star has moved up in the image, so we want to move it back down,
            # meaning we need to move the telescope up
            else:
                ydirection = 'down'
            # Star has moved down in the image, so we want to move it back up,
            # meaning we need to move the telescope down
            xjog_distance = abs(separation * np.cos(deltangle)) * 0.350 * \
                            0.75
            yjog_distance = abs(separation * np.sin(deltangle)) * 0.350 * \
                            0.50
            jog_separation = np.sqrt(xjog_distance ** 2 + yjog_distance ** 2)
            if jog_separation >= 100:
                print('Guide star has moved substantially between images...If the telescope did not move '
                      'suddenly, the guide star most likely has become saturated and the guider has '
                      'picked a new star.')
                x_initial += (x - x_0)
                y_initial += (y - y_0)
            elif jog_separation < 100:
                print('Guider is making an adjustment')
                print('xdistance: {}; ydistance: {}'.format(xjog_distance, yjog_distance))
                print('Delta Angle: {}'.format(deltangle))
                print('Separation: {}'.format(separation))
                print('Direction: {} {}'.format(xdirection, ydirection))
                tel.onThread(tel.jog, xdirection, xjog_distance)
                tel.slew_done.wait()
                tel.onThread(tel.jog, ydirection, yjog_distance)
                tel.slew_done.wait()
                moved = True
        i += 1
        if moved:
            i += 1


if __name__ == '__main__':
    config = ObjectReader(Reader(r'C:/Users/GMU Observtory1/-omegalambda/config/parameters_config.json'))
    tel = Telescope()
    tel.start()
    time.sleep(5)
    tel.onThread(tel.unpark)
    guide_test_func()
    time.sleep(5)
    tel.onThread(tel.park)
    tel.onThread(tel.disconnect)
    tel.onThread(tel.stop)
