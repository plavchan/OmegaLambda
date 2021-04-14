# Filereader Utils for Focuser & Guider
import logging
import numpy as np
# import matplotlib.pyplot as plt
from typing import Union, Optional, Tuple

import photutils
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from scipy.optimize import curve_fit

from ..IO import config_reader

np.warnings.filterwarnings('ignore')


def mediancounts(image_path: str) -> float:
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
    
    
def findstars(path: str, saturation: Union[int, float], subframe: Optional[Tuple[int]] = None,
              return_data: bool = False):
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
    Tuple
        Returns a tuple with the first element being a list of stars where each star is a tuple with
        (x position, y position).  The second element is a list of peak count values.

    """
    image = fits.getdata(path)
    logging.debug('Image data read sucessfully from {}'.format(path))
    mean, median, stdev = sigma_clipped_stats(image, sigma=3)
    data = (image - median) ** 2
    threshold = photutils.detect_threshold(image, nsigma=5)
    if not subframe:
        starfound = photutils.find_peaks(data, threshold=threshold, box_size=50, border_width=500,
                                         centroid_func=photutils.centroids.centroid_com)
    else:
        config_dict = config_reader.get_config()
        r = config_dict.guider_max_move / config_dict.plate_scale * 1.5
        x_cent = subframe[0]
        y_cent = subframe[1]
        data_subframe = data[int(y_cent - r):int(y_cent + r), int(x_cent - r):int(x_cent + r)]
        image = image[int(y_cent - r):int(y_cent + r), int(x_cent - r):int(x_cent + r)]
        threshold = threshold[int(y_cent - r):int(y_cent + r), int(x_cent - r):int(x_cent + r)]
        starfound = photutils.find_peaks(data_subframe, threshold=threshold, box_size=50, border_width=10,
                                         centroid_func=photutils.centroids.centroid_com)

    n = 0
    stars = []
    peaks = []
    if starfound:
        for _ in starfound:
            bad_pixel = False
            x_cent = starfound['x_peak'][n]
            y_cent = starfound['y_peak'][n]
            peak = image[y_cent, x_cent]
            n += 1
            if peak >= (saturation * 2) ** 2:
                bad_pixel = True
            pixels = [(y_cent, x_cent + 1), (y_cent, x_cent - 1), (y_cent + 1, x_cent), (y_cent - 1, x_cent)]
            for value in pixels:
                if image[value[0], value[1]] < 1.2 * median:
                    bad_pixel = True
            if bad_pixel:
                continue
            star = (x_cent, y_cent)
            stars.append(star)
            peaks.append(peak)

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


def radial_average(path: str, saturation: Union[int, float]) -> Tuple[Optional[Union[float, int]],
                                                                      Union[float, int], bool]:
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
    fwhm_final : LIST
        The fwhm of the brightest unsaturated star in the image, or the median fwhm if all stars are saturated.
        If no fwhm was found, returns None.

    """
    stars, peaks, data, stdev = findstars(path, saturation, return_data=True)
    r_ = 30
    fwhm_list = []
    # a = 0
    for star in stars:
        x_cent = star[0]
        y_cent = star[1]
        star = data[int(y_cent-r_):int(y_cent+r_), int(x_cent-r_):int(x_cent+r_)]
        starx, stary = np.indices(star.shape)
        r = np.sqrt((stary - r_)**2 + (starx - r_)**2)
        r = r.astype(np.int)

        tbin = np.bincount(r.ravel(), star.ravel())
        nr = np.bincount(r.ravel())
        radialprofile = tbin / nr
       
        if len(radialprofile) != 0:
            maximum = max(radialprofile)
            if maximum == 0:
                continue
            else:
                radialprofile = radialprofile / maximum
            f = np.linspace(0, len(radialprofile)-1, len(radialprofile))
            mean = np.mean(radialprofile)
            sigma = np.std(radialprofile)
            try:
                popt, pcov = curve_fit(gaussianfit, f, radialprofile, p0=[1 / (np.sqrt(2 * np.pi)), mean, sigma])
                g = np.linspace(0, len(radialprofile)-1, 10*len(radialprofile))
                function = gaussianfit(g, *popt)
                for x in range(len(function)):
                    if function[x] <= (1/2):
                        fwhm = 2*g[x]
                        fwhm_list.append(fwhm)
                        break
            except RuntimeError:
                logging.debug("Could not find a Gaussian Fit...using whole pixel values to estimate fwhm")
                for x in range(len(radialprofile)):
                    if radialprofile[x] <= (1/2):
                        fwhm = 2*f[x]
                        fwhm_list.append(fwhm)
                        break

        else:
            logging.error('Radial profile has length of 0...')
            continue

    fwhm_peaks = np.array((fwhm_list, peaks))
    fwhm_peaks = np.delete(fwhm_peaks, np.where(fwhm_peaks[0, :] < 3), 1)
    if not np.any(fwhm_peaks):
        return None, -1, False

    saturated_peak = max(fwhm_peaks[1, :])
    saturated = (saturated_peak >= saturation * 2)
    highest_peak = 0
    for i in range(len(fwhm_peaks[0, :])):
        if fwhm_peaks[1, highest_peak] < fwhm_peaks[1, i] <= saturation * 2:
            highest_peak = i
    if highest_peak != -1:
        fwhm_final = fwhm_peaks[0, highest_peak]
        fwhm_peak = fwhm_peaks[1, highest_peak]
    else:
        fwhm_final = float(np.median(fwhm_peaks[0, :]))
        fwhm_peak = -1

    return fwhm_final, fwhm_peak, saturated


"""
Gaussian plot for future reference:

            if a < 1:
                 plt.plot(f, radialprofile, 'b+:', label='data')
                 plt.plot(f, gaussianfit(f, *popt), 'ro:', label='fit')
                 plt.plot([0, fwhm/2], [1/2, 1/2], 'g-.')
                 plt.plot([fwhm/2, fwhm/2], [0, 1/2], 'g-.', label='HWHM')
                 plt.legend()
                 plt.xlabel('x position, HWHM = {}'.format(fwhm/2))
                 plt.ylabel('normalized counts')
                 plt.grid()
                 plt.savefig(r'C:/Users/GMU Observtory1/-omegalambda/test/GaussianPlot.png')
                 a += 1

"""