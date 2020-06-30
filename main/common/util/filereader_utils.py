# Filereader Utils for Focuser & Guider
import logging
import statistics

import photutils
from astropy.io import fits
from astropy.stats import sigma_clipped_stats

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
    iraffind = photutils.IRAFStarFinder(threshold = 3.5*stdev, fwhm = 15, sigma_radius = 2, peakmax = 40000, exclude_border = True)
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