# Filereader Utils for Focuser & Guider
import logging
import os
import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from typing import Union, Optional, Tuple

import photutils
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from photutils.aperture import CircularAperture, CircularAnnulus
import threading

from numba import jit, njit, prange

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


@njit(parallel=True, nogil=True)
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


@jit(parallel=True, nogil=True)
def _get_all_fwhm(stars, peaks, data, ri, sky, binsize):
    fwhm_list = np.empty((len(stars),), dtype=np.float64)
    snrs = np.empty((len(stars),), dtype=np.float64)
    xarr = np.empty((len(stars),), dtype=np.ndarray)
    yarr = np.empty((len(stars),), dtype=np.ndarray)
    rarr = np.empty((len(stars),), dtype=np.ndarray)
    stararr = np.empty((len(stars),), dtype=np.ndarray)

    for ii in prange(len(stars)):
        x_cent = stars[ii][0]
        y_cent = stars[ii][1]
        star = data[int(y_cent - ri):int(y_cent + ri), int(x_cent - ri):int(x_cent + ri)] + sky
        centroidx, centroidy = photutils.centroids.centroid_com(star, oversampling=1)
        stary, starx = np.indices(star.shape)
        r = np.hypot(starx - centroidx, stary - centroidy).astype(np.float64)

        nbins = int(np.round(r.max() / binsize) + 1)
        maxbin = nbins * binsize
        bins, interp_points = np.linspace(0, maxbin, nbins + 1), np.arange(0, maxbin + .01, .01)
        r, star = r.ravel(), star.ravel()
        radialprofile = np.histogram(r, bins, weights=star)[0] / np.histogram(r, bins)[0]
        radialprofile = np.interp(interp_points, bins[1:][radialprofile == radialprofile], radialprofile[radialprofile == radialprofile])

        target_counts = (np.nanmax(radialprofile) + np.nanmin(radialprofile))/2
        # radialprofile /= maximum
        fwhm_list[ii] = 0
        for xi in np.arange(len(radialprofile) - 1, -1, -1):
            if radialprofile[xi] >= target_counts:
                fwhm_list[ii] = 2 * interp_points[xi]
                break
        # Signal to noise ratio of target, to be used as a weight
        snrs[ii] = (peaks[ii] - sky) / np.sqrt(peaks[ii] + sky)
        if fwhm_list[ii] < 3 or fwhm_list[ii] > 50:
            snrs[ii] = 0

        xarr[ii] = interp_points
        yarr[ii] = radialprofile
        rarr[ii] = r
        stararr[ii] = star

    peaks = np.array(peaks, dtype=np.float64)
    saturation_index = np.argmax(peaks)
    fwhm_peak = peaks[saturation_index]
    fwhm_final = float(np.nansum(fwhm_list * snrs) / np.nansum(snrs))

    return fwhm_final, fwhm_peak, fwhm_list, snrs, xarr, yarr, rarr, stararr


def radial_average(path: str, saturation: Union[int, float], plot_lock=None, image_save_path=None) -> Tuple[Optional[Union[float, int]], Union[float, int]]:
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
    plot_lock : threading.Lock
        To prevent multiple plots from drawing across threads at once.

    Returns
    -------
    fwhm_final : LIST
        The fwhm of the brightest unsaturated star in the image, or the median fwhm if all stars are saturated.
        If no fwhm was found, returns None.

    """
    stars, peaks, data, stdev = findstars(path, saturation, return_data=True)
    sky = mediancounts(path)
    r_ = 30
    binsize = 0.5
    fwhm_final, fwhm_peak, fwhm_list, snrs, xarr, yarr, rarr, stararr = _get_all_fwhm(stars, peaks, data, r_, sky, binsize)

    if plot_lock:
        plot_lock.acquire()
    imdata = fits.getdata(path)
    plt.imshow(imdata, cmap='gray', norm=colors.Normalize(vmin=np.nanmedian(imdata), vmax=np.nanmedian(imdata) + 400))
    plt.gca().invert_yaxis()
    plt.colorbar()
    for i, star in enumerate(stars):
        aperture = CircularAperture(star, r=5)
        aperture.plot(color='blue', lw=2)
        plt.text(star[0]+20, star[1]+20, s='{}'.format(i+1), color='blue')

    if not image_save_path:
        current_path = os.path.abspath(os.path.dirname(__file__))
        target_path = os.path.join(current_path, r'../../../test/FocusApertures_{}.png'.format(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')))
        plt.savefig(target_path, dpi=300)
    else:
        plt.savefig(os.path.join(image_save_path, 'FocusApertures_{}.png'.format(datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))), dpi=300)
    plt.close()

    fig, ax = plt.subplots(ncols=2, nrows=2)
    highest_snr = np.argsort(snrs)[::-1][:4]
    highest_fwhm = fwhm_list[highest_snr]
    highest_x = xarr[highest_snr]
    highest_y = yarr[highest_snr]
    highest_r = rarr[highest_snr]
    highest_star = stararr[highest_snr]
    for n in range(len(highest_r)):
        i = 0 if n <= 1 else 1
        j = int((n + 1) % 2 == 0)
        ax[j, i].scatter(highest_r[n], highest_star[n], c='b', s=2)
        ax[j, i].plot(highest_x[n], highest_y[n], 'r-')
        ax[j, i].set_title('SNR = {:.3f}, FWHM = {:.3f}'.format(snrs[highest_snr][n], highest_fwhm[n]))
        ax[j, i].set_xlabel('Radial distance [px]')
        ax[j, i].set_ylabel('Counts')
    fig.subplots_adjust(wspace=.5, hspace=.5)
    fig.suptitle('Radial Profiles for 4 Highest SNR stars')
    if not image_save_path:
        current_path = os.path.abspath(os.path.dirname(__file__))
        target_path = os.path.join(current_path, r'../../../test/FocusProfiles_{}.png'.format(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')))
        plt.savefig(target_path, dpi=300)
    else:
        plt.savefig(os.path.join(image_save_path, 'FocusProfiles_{}.png'.format(datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))), dpi=300)
    plt.close()
    if plot_lock:
        plot_lock.release()

    return fwhm_final, fwhm_peak