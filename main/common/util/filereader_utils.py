# Filereader Utils for Focuser & Guider
import logging
import statistics
import numpy as np
# import matplotlib.pyplot as plt

import photutils
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from scipy.optimize import curve_fit

def FindStars(path, saturation, return_data=False):
    '''
    Description
    -----------
    Finds the star centroids in an image

    Parameters
    ----------
    path : STR
        Path to fits image file with stars in it.
    saturation : INT
        Number of counts for a star to be considered saturated for a specific CCD Camera.
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
    threshold = photutils.detect_threshold(image, nsigma = 5)
    data = (image - median)**2
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
        return (stars, peaks, image - median, stdev)
    
def GaussianFit(x,a,x0,sigma):
    return a*np.exp(-(x-x0)**2/(2*sigma**2))

def Radial_Average(path, saturation):
    '''
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

    '''
    stars, peaks, data, stdev = FindStars(path, saturation, return_data=True)
    R = 25
    fwhm_list = []
    # a = 0
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
            maximum = max(radialprofile)
            f = np.linspace(0, len(radialprofile), len(radialprofile))
            mean = np.mean(radialprofile)
            sigma = np.std(radialprofile)
            try:
                popt, pcov = curve_fit(GaussianFit, f, radialprofile, p0=[maximum, mean, sigma])
                g = np.linspace(0, len(radialprofile), 10*len(radialprofile))
                function = GaussianFit(g, *popt)
            except:
                print("Could not find a Gaussian Fit...skipping to the next star")
                continue
            run = True
            for x in range(len(g)):
                if run == True:
                    if function[x] <= (maximum/2):
                        #print('HWHM = {}'.format(num))
                        FWHM = 2*g[x]
                        fwhm_list = np.append(fwhm_list, FWHM)
                        run = False
                elif run == False:
                    break

                
                # graphing stuff 
                
                # plt.figure()
                # plt.imshow(star, cmap = 'YlGn')
               
                # if a <= 1:
                #     # fig,ax=plt.subplots()
                #     # ax.plot(f,radialprofile)
                #     plt.plot(f, radialprofile, 'b+:', label='data')
                #     plt.plot(f, GaussianFit(f, *popt), 'ro:', label='fit')
                #     plt.legend()
                #     plt.xlabel('x position')
                #     plt.ylabel('counts')
                #     plt.show()
                #     plt.savefig(r'C:/Users/GMU Observtory1/-omegalambda/test/plot.png')
                #     a += 1
                
        mask = [fwhm >= 4 for fwhm in fwhm_list]

    return fwhm_list[mask]