from ..main.common.util import filereader_utils
import matplotlib.pyplot as plt
import photutils
from numpy import sqrt


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
            dist_next = sqrt((stars[i][0] - stars[i+1][0])**2 + (stars[i][1] - stars[i+1][1])**2)
            dist_prev = sqrt((stars[i][0] - stars[i-1][0])**2 + (stars[i][1] - stars[i-1][1])**2)
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
            distance = sqrt((star[0] - 250) ** 2 + (star[1] - 250) ** 2)
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
        r'H:\Observatory Files\Observing Sessions\2020_Data\20200711\TIC273035189-12_120s_R-0090.fit', 1
    )
    x_initial = star[0]
    y_initial = star[1]
    i = 0
    while i < 10:
        moved = False
        star = find_guide_star(
            r'H:\Observatory Files\Observing Sessions\2020_Data\20200711\TIC273035189-12_120s_R-{0:04d}.fit'.format(i + 91),
            iteration=i+2, subframe=(x_initial, y_initial))
        x_0 = 250
        y_0 = 250
        x = star[0]
        y = star[1]
        print('Image number: {0:04d}'.format(i + 91))
        print('Initial coordinates: x={}, y={}'.format(x_initial, y_initial))
        print('Guide star relative coordinates: x={}, y={}'.format(x, y))
        if abs(x - x_0) >= 25.0:
            xdistance = x - x_0
            direction = None
            if xdistance >= 0:
                direction = 'right'
            # Star has moved right in the image, so we want to move it back left,
            # meaning we need to move the telescope right
            elif xdistance < 0:
                direction = 'left'
            # Star has moved left in the image, so we want to move it back right,
            # meaning we need to move the telescope left
            jog_distance = abs(xdistance) * 0.75
            if jog_distance >= 100:
                print('Guide star has moved substantially between images...If the telescope did not move '
                      'suddenly, the guide star most likely has become saturated and the guider has '
                      'picked a new star.')
                x_initial += (x - x_0)
                y_initial += (y - y_0)
            elif jog_distance < 100:
                print('Guider is making an adjustment in RA')
                print('Jog distance x: {} pixels'.format(jog_distance))
                moved = True
        if abs(y - y_0) >= 25.0:
            ydistance = y - y_0
            direction = None
            if ydistance >= 0:
                direction = 'up'
            # Star has moved up in the image, so we want to move it back down,
            # meaning we need to move the telescope up
            elif ydistance < 0:
                direction = 'down'
            # Star has moved down in the image, so we want to move it back up,
            # meaning we need to move the telescope down
            jog_distance = abs(ydistance)*0.50
            if jog_distance >= 100:
                print('Guide star has moved substantially between images...If the telescope did not move '
                      'suddenly, the guide star most likely has become saturated and the guider has '
                      'picked a new star.')
                x_initial += (x - x_0)
                y_initial += (y - y_0)
            elif jog_distance < 100:
                print('Guider is making an adjustment in Dec')
                print('Jog distance y: {} pixels'.format(jog_distance))
                moved = True
            print('Moved = {}'.format(moved))
        i += 1
        if moved:
            i += 1


if __name__ == '__main__':
    guide_test_func()
