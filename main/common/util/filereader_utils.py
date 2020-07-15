# Filereader Utils for Focuser & Guider
import logging
import statistics
import numpy as np
# import matplotlib.pyplot as plt

import photutils
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from scipy.optimize import curve_fit

focus_star = None


def mediancounts(image_path):
    """
    Parameters
    ----------
    image_path : STR
        Path to image file to calculate median counts for.

    Returns
    -------
    median : FLOAT
        Median counts of the specified image file.

    """
    image = fits.getdata(image_path)
    mean, median, stdev = sigma_clipped_stats(image, sigma=3)
    return median
    
    
def findstars(path, saturation, subframe=None, return_data=False):
    """
    Description
    -----------
    Finds the star centroids in an image

    Parameters
    ----------
    path : STR
        Path to fits image file with stars in it.
    saturation : INT
        Number of counts for a star to be considered saturated for a specific CCD Camera.
    subframe : TUPLE
        Tuple with x coordinate and y coordinate of the star to create a subframe around.
    return_data : BOOL, optional
        If True, returns the image data and the standard deviation as well.  Mostly used for Radial_Average.
        The default is False.

    Returns
    -------
    LIST
        List of stars, each star is a tuple with (x position, y position).

    """
    image = fits.getdata(path)
    mean, median, stdev = sigma_clipped_stats(image, sigma=3)
    data = (image - median)**2
    threshold = photutils.detect_threshold(image, nsigma=5)
    if not subframe:
        starfound = photutils.find_peaks(data, threshold=threshold, box_size=50, border_width=250,
                                         centroid_func=photutils.centroids.centroid_com)
    else:
        r = 250
        x_cent = subframe[0]
        y_cent = subframe[1]
        xmin = int(x_cent - r)
        xmax = int(x_cent + r)
        ymin = int(y_cent - r)
        ymax = int(y_cent + r)
        data_subframe = data[ymin:ymax, xmin:xmax]
        image = image[ymin:ymax, xmin:xmax]
        threshold = threshold[ymin:ymax, xmin:xmax]
        starfound = photutils.find_peaks(data_subframe, threshold=threshold, box_size=50, border_width=10,
                                         centroid_func=photutils.centroids.centroid_com)
    n = 0
    stars = []
    peaks = []
    for _ in starfound:
        bad_pixel = False
        x_cent = starfound['x_peak'][n]
        y_cent = starfound['y_peak'][n]
        peak = image[y_cent, x_cent]
        if peak >= (saturation*2)**2:
            bad_pixel = True
        pixels = [(y_cent, x_cent + 1), (y_cent, x_cent - 1), (y_cent + 1, x_cent), (y_cent - 1, x_cent)]
        for value in pixels:
            if image[value[0], value[1]] < 1.2*median:
                bad_pixel = True
        if bad_pixel: 
            n += 1
            continue
        star = (x_cent, y_cent)
        stars.append(star)
        peaks.append(peak)
        n += 1
    if not return_data:
        return stars, peaks
    else:
        return stars, peaks, image - median, stdev


def gaussianfit(x, a, x0, sigma):
    """
    Gaussian Fit Function

    Parameters
    ----------
    x : FLOAT
        x data.
    a : FLOAT
        Amplitude constant.
    x0 : FLOAT
        Initial x.
    sigma : FLOAT
        Standard deviation.

    Returns
    -------
    y
        Y value corresponding to input x value.

    """
    return a*np.exp(-(x-x0)**2/(2*sigma**2))


def radial_average(path, saturation):
    """
    Description
    -----------
    Finds the median fwhm of an image.

    Parameters
    ----------
    path : STR
        File path to fits image to get fwhm from.
    saturation : INT
        Number of counts for a star to be considered saturated for a specific CCD Camera.

    Returns
    -------
    median_fwhm : INT
        The median fwhm measurement of the stars in the fits image.

    """
    global focus_star
    stars, peaks, data, stdev = findstars(path, saturation, subframe=focus_star, return_data=True)
    r_ = 30
    fwhm_list = np.ndarray((0,))
    # a = 0
    for star in stars:
        x_cent = star[0]
        y_cent = star[1]
        ymin = int(y_cent-r_)
        ymax = int(y_cent+r_)
        xmin = int(x_cent-r_)
        xmax = int(x_cent+r_)
        star = data[ymin:ymax, xmin:xmax]
        starx, stary = np.indices(star.shape)
        r = np.sqrt((stary - r_)**2 + (starx - r_)**2)
        r = r.astype(np.int)

        tbin = np.bincount(r.ravel(), star.ravel())
        nr = np.bincount(r.ravel())
        radialprofile = tbin / nr
       
        if len(radialprofile) != 0:
            maximum = max(radialprofile)
            radialprofile = radialprofile/maximum
            f = np.linspace(0, len(radialprofile), len(radialprofile))
            mean = np.mean(radialprofile)
            sigma = np.std(radialprofile)
            try:
                popt, pcov = curve_fit(gaussianfit, f, radialprofile, p0=[1 / (np.sqrt(2 * np.pi)), mean, sigma])
                g = np.linspace(0, len(radialprofile), 10*len(radialprofile))
                function = gaussianfit(g, *popt)
            except:
                logging.debug("Could not find a Gaussian Fit...skipping to the next star")
                continue
            run = True
            fwhm = None
            for x in range(len(g)):
                if run:
                    if function[x] <= (1/2):
                        fwhm = 2*g[x]
                        fwhm_list = np.append(fwhm_list, fwhm)
                        run = False
                elif not run:
                    break
                
            # if a < 1:
            #     plt.plot(f, radialprofile, 'b+:', label='data')
            #     plt.plot(f, gaussianfit(f, *popt), 'ro:', label='fit')
            #     plt.plot([0, fwhm/2], [1/2, 1/2], 'g-.')
            #     plt.plot([fwhm/2, fwhm/2], [0, 1/2], 'g-.', label='HWHM')
            #     plt.legend()
            #     plt.xlabel('x position, HWHM = {}'.format(fwhm/2))
            #     plt.ylabel('normalized counts')
            #     plt.grid()
            #     plt.savefig(r'C:/Users/GMU Observtory1/-omegalambda/test/GaussianPlot.png')
            #     a += 1
    
    fwhm_list = [i for i in fwhm_list if i > 3]
    if fwhm_list:
        fwhm_med = statistics.median(fwhm_list)
    else:
        print('No fwhm calculations can be made from the image')
        return None

    if not focus_star:
        i = 0
        j = 0
        while i < len(stars) - j:
            if peaks[i] >= saturation:
                peaks.pop(i)
                stars.pop(i)
                j += 1
            i += 1
        if peaks:
            maxindex = peaks.index(max(peaks))
            focus_star = stars[maxindex]
        else:
            focus_star = None

    return fwhm_med
