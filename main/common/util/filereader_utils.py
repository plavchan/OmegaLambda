# Filereader Utils for Focuser & Guider
import logging
import statistics
import numpy as np

import photutils
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
# import matplotlib.pyplot as plt

def IRAF_calculations(path, **kwargs):
    '''
    Description
    -----------
    Does an IRAF calculation for the parameters specified in kwargs.

    Parameters
    ----------
    path : STR
        File path to the image to do calculations on.
    **kwargs : DICT, optional
        Keywords for which values you want returned.  Accepts 'fwhm', 'stars', and 'centroids'.  Set 
        value = True to return that value.  The default is None, which returns all values.

    Returns
    -------
    results : LIST
        List with all values specified by kwargs.

    '''
    logging.info('Starting IRAF calculations...')
    image = fits.getdata(path)
    mean, median, stdev = sigma_clipped_stats(image, sigma = 3)
    iraffind = photutils.IRAFStarFinder(threshold = 3.5*stdev, fwhm = 10, sigma_radius = 2, peakmax = 40000, exclude_border = True)
    fitsfile = iraffind(image)
    FWHM = statistics.median(fitsfile['fwhm'])
    stars = len(fitsfile)
    xcentroids = fitsfile['xcentroid']
    ycentroids = fitsfile['ycentroid']
    fluxes = fitsfile['flux']
    logging.info('Finished IRAF calculations...')
    results = []
    for key, value in kwargs.items():
        if key == 'FWHM' and value == True:
            results.append(FWHM)
        elif key =='stars' and value == True:
            results.append(stars)
        elif key == 'centroids' and value == True:
            results.append(xcentroids)
            results.append(ycentroids)
        elif key =='fluxes' and value == True:
            results.append(fluxes)
    if not results:
        results = fitsfile
    return results

def GaussianFit(x, a, x0, sigma):
    return a*exp(-(x-x0)**2/(2*sigma**2))

def Radial_Average(path):

    image = fits.getdata(path)
    mean, median, stdev = sigma_clipped_stats(image, sigma = 3)
    threshold = photutils.detect_threshold(image, nsigma = 15)
    starfound = photutils.find_peaks(image, threshold = threshold)
    R = 12
    r = list(range(0,4096))
    data = image - median
    pix_x, pix_y = np.indices((data.shape))
    n = 0
    fwhm_list = []

    for row in starfound:
    
        x_cent = starfound['x_peak'][n]
        y_cent = starfound['y_peak'][n]
        n = n+1
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
            if radialprofile[2] > (10 +stdev):
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
        median_fwhm = statistics.median(fwhm_list[mask])

    return median_fwhm