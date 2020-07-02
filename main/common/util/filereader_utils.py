# Filereader Utils for Focuser & Guider
import logging
import statistics
import numpy as np
# import matplotlib.pyplot as plt

import photutils
from astropy.io import fits
from astropy.stats import sigma_clipped_stats

def FindStars(path, return_data=False):
    '''
    Description
    -----------
    Finds the star centroids in an image

    Parameters
    ----------
    path : STR
        Path to fits image file with stars in it.
    return_data : BOOL, optional
        If True, returns the image data and the standard deviation as well.  Mostly used for Radial_Average.
        The default is False.

    Returns
    -------
    LIST
        List of stars, each star is a tuple with (x position, y position).

    '''
    image = fits.getdata(path)
    mean, median, stdev = sigma_clipped_stats(image, sigma = 3)
    threshold = photutils.detect_threshold(image, nsigma = 3)
    data = image - median
    # data_0 = photutils.segmentation.detect_sources(image, threshold = threshold, npixels = 20)
    # threshold = photutils.detect_threshold(data_0, nsigma = 3)
    starfound = photutils.find_peaks(data, threshold = threshold, box_size = 50, border_width = 20)
    n = 0
    stars = []
    peaks = []
    for row in starfound:
        bad_pixel = False
        x_cent = starfound['x_peak'][n]
        y_cent = starfound['y_peak'][n]
        peak = image[y_cent, x_cent]
        # if n > 0:
        #     if abs(x_cent - starfound['x_peak'][n - 1]) <= 10 or abs(y_cent - starfound['y_peak'][n - 1]) <= 10:
        #         bad_pixel = True
        if peak >= 40000:
            bad_pixel = True
        pixels = [(y_cent, x_cent + 1), (y_cent, x_cent - 1), (y_cent + 1, x_cent), (y_cent - 1, x_cent)]
        for value in pixels:
            if image[value[0], value[1]] < median:
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
        return (stars, peaks, image - median, stdev)

def Radial_Average(path):
    '''
    Description
    -----------
    Finds the median fwhm of an image.

    Parameters
    ----------
    path : STR
        File path to fits image to get fwhm from.

    Returns
    -------
    median_fwhm : INT
        The median fwhm measurement of the stars in the fits image.

    '''
    stars, peaks, data, stdev = FindStars(path, return_data=True)
    R = 12
    fwhm_list = []
    for star in stars:
        x_cent = star[0]
        y_cent = star[1]
        xmin = int(x_cent - R)
        xmax = int(x_cent + R)
        ymin = int(y_cent - R)
        ymax = int(y_cent + R)
        star = data[ymin:ymax, xmin:xmax]
        starx, stary = np.indices((star.shape))
        r = np.sqrt((stary - R)**2 + (starx - R)**2)
        r = r.astype(np.int)

        tbin = np.bincount(r.ravel(), star.ravel())
        nr = np.bincount(r.ravel())
        radialprofile = tbin / nr

       
        if len(radialprofile) != 0:
            maximum = radialprofile[0]
            if radialprofile[2] > (10 + stdev):
                num = int(0)
                run = True
                for x in radialprofile:
                    if run == True:
                        if radialprofile[num] <= (maximum/2):
                            #print('HWHM = {}'.format(num))
                            FWHM = num*2
                            fwhm_list = np.append(fwhm_list, FWHM)
                            run = False

                        num = num + 1
                    elif run == False:
                        break
                
                # graphing stuff 
                
                # plt.figure()
                # plt.imshow(star, cmap = 'YlGn')
                # if z == 4:
                #       f = list(range(0,len(radialprofile)))
                #     # fig,ax=plt.subplots()
                #     # ax.plot(f,radialprofile)
                #     plt.plot(f, radialprofile, 'b+:', label='data')
                #     plt.plot(f, GaussianFit(f, *popt), 'ro:', label='fit')
                #     plt.legend()
                #     plt.xlabel('x position')
                #     plt.ylabel('flux')
                #     plt.show()
                #     plt.savefig(r'C:/Users/GMU Observtory1/-omegalambda/test/plot.png')
                
        mask = [fwhm >= 4 for fwhm in fwhm_list]

    return fwhm_list[mask]