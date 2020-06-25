# Filereader Utils for Focuser & Guider
import logging
import photutils
import statistics
from astropy.io import fits
from astropy.stats import sigma_clipped_stats

def get_FWHM_from_image(path):
    '''

    Parameters
    ----------
    path : STR
        File path to the fits image to read FWHM from.

    Returns
    -------
    FWHM : FLOAT
        Float number of median FWHM from all stars in the image, in PIXELS (we will want to convert this to arcseconds).

    '''
    logging.info('Starting IRAF fwhm calculations...')
    image = fits.getdata(path)
    mean, median, stdev = sigma_clipped_stats(image, sigma = 3)
    iraffind = photutils.IRAFStarFinder(fwhm = 10, threshold = 5*stdev)
    fitsfile = iraffind(image)
    FWHM = statistics.median(fitsfile['fwhm'])
    length = len(fitsfile)
    logging.info('Finished IRAF fwhm calculations:  Median fwhm = {}'.format(FWHM))
    logging.info('Number of stars: {}'.format(length))
    return FWHM