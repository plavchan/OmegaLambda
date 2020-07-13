import math
import datetime

from astropy import units as u
from astropy.coordinates import SkyCoord, FK5, get_sun
from astropy.time import Time

from . import time_utils

def convert_degrees_to_radians(Degrees):
    '''
    Parameters
    ----------
    Degrees: LIST, FLOAT
        Value in degrees
    
    Returns
    -------
    LIST, FLOAT
        Degree value(s) in Radians
    '''
    if type(Degrees) is list:   
        result = []
        for element in Degrees:
            result.append(element*math.pi/180)
        return result
    else:
        return (Degrees*math.pi/180)

def convert_radians_to_degrees(Radians):
    '''
    Parameters
    ---------
    Radians: LIST, FLOAT
        Any value in Radians
        
    Returns
    -------
    LIST, FLOAT
        Radian value(s) in degrees
    '''
    if type(Radians) is list:    
        result = []
        for element in Radians:
            result.append(element*180/math.pi)
        return result
    else:
        return (Radians*180/math.pi)

def get_decHA_from_AltAz(azimuth, altitude, latitude):
    '''
    Parameters
    ----------
    azimuth : FLOAT
        The azimuth of intended target.
    altitude : FLOAT
        The altitude of intended target.
    latitude : FLOAT
        The latitude of observatory.
        
    Returns
    -------
    dec : FLOAT
        The calculated declination of the target.
    HA : FLOAT
        The calculated hour angle of intended target.
    '''
    (azimuth_r, altitude_r, latitude_r) = convert_degrees_to_radians([azimuth, altitude, latitude])
    dec_r = math.asin(math.sin(altitude_r)*math.sin(latitude_r)+math.cos(altitude_r)*math.cos(latitude_r)*math.cos(azimuth_r))
    HA_r = math.acos((math.sin(altitude_r) - math.sin(latitude_r)*math.sin(dec_r))/(math.cos(latitude_r)*math.cos(dec_r)))
    if math.sin(azimuth_r) > 0:
        HA_r = 2*math.pi - HA_r
    (dec, HA) = convert_radians_to_degrees([dec_r, HA_r])
    return (dec, HA)
    
def convert_AltAz_to_RaDec(azimuth, altitude, latitude, longitude, time):
    '''
    Parameters
    ----------
    azimuth : FLOAT
        The azimuth of the intended target.
    altitude : FLOAT
        The altitude of the intended target.
    latitude : FLOAT
        The lattitude of the observatory.
    longitude : FLOAT
        The longitude of the observatory.
    time : datetime.datetime object
        Time to be converted.
        
    Returns
    -------
    ra : FLOAT
        The calculated Right Ascension from Alt/Az.
    dec : FLOAT
        The calculated Declination from Alt/Az.
    '''
    LST = time_utils.get_local_sidereal_time(longitude, time)
    LST = LST*15
    (dec, HA) = get_decHA_from_AltAz(azimuth, altitude, latitude)
    ra = (LST - HA)/15
    while ra < 0:
        ra += 24
    while ra > 24:
        ra -= 24
    return (ra, dec)

def convert_RaDec_to_AltAz(ra, dec, latitude, longitude, time):
    '''
    Parameters
    ----------
    ra : FLOAT
        Given right ascension of target.
    dec : FLOAT
        Given declination of target.
    latitude : FLOAT
        Lattitude of observatory.
    longitude : FLOAT
        Longitude of observatory.
    time : datetime.datetime object
        Time to be converted.
        
    Returns
    -------
    az : FLOAT
        Calculated azimuth of target.
    alt : FLOAT
        Calculated altitude of target.
    '''
    LST = time_utils.get_local_sidereal_time(longitude, time)
    HA = (LST - ra)*15
    while HA < 0:
        HA += 360
    while HA > 360:
        HA -= 360
    (dec_r, latitude_r, longitude_r, HA_r) = convert_degrees_to_radians([dec, latitude, longitude, HA])
    alt_r = math.asin(math.sin(dec_r)*math.sin(latitude_r)+math.cos(dec_r)*math.cos(latitude_r)*math.cos(HA_r))
    az_r = math.acos((math.sin(dec_r) - math.sin(alt_r)*math.sin(latitude_r))/(math.cos(alt_r)*math.cos(latitude_r)))
    if math.sin(HA_r) > 0:
        az_r = 2*math.pi - az_r
    (az, alt) = convert_radians_to_degrees([az_r, alt_r])
    return (az, alt)

def convert_J2000_to_apparent(ra, dec):
    '''
    Parameters
    ----------
    ra : FLOAT
        Right ascension to be converted from J2000 coordinates to apparent 
        cordinates.
    dec : FLOAT
        Declination to be converted from J2000 coordinates to apparent coordinates.
        
    Returns
    -------
    coords_apparent.ra.hour: FLOAT
        Right ascension of target in local topocentric coordinates ("JNow").
    coords_apparent.dec.degree: FLOAT
        Declination of target in local topocentric coordinates ("JNow").
    '''
    year = time_utils.current_decimal_year()
    coords_J2000 = SkyCoord(ra = ra*u.hourangle, dec = dec*u.degree, frame = 'icrs') #ICRS Equinox is always J2000
    coords_apparent = coords_J2000.transform_to(FK5(equinox='J{}'.format(year)))
    return (coords_apparent.ra.hour, coords_apparent.dec.degree)

def get_sun_elevation(time, latitude, longitude):
    '''
    Parameters
    ----------
    time : datetime.datetime object
        Time to get sun elevation for.
    latitude : FLOAT
        Latitude at which to calculate sun elevation.
    longitude : FLOAT
        Longitude at which to calculate sun elevation.

    Returns
    -------
    alt : FLOAT
        Degrees above/below the horizon that the Sun is located at for the specified
        time at the specified coordinates.  Negative = below horizon.

    '''
    if type(time) is not datetime.datetime:
        time = time_utils.convert_to_datetime_UTC(time)
    astrotime = Time(time, format='datetime', scale='utc')
    coords = get_sun(astrotime)
    (az, alt) = convert_RaDec_to_AltAz(float(coords.ra.hour), float(coords.dec.degree), latitude, longitude, time)
    return alt

def get_sunset(day, latitude, longitude):
    '''
    Parameters
    ----------
    day : datetime.datetime object
        Day to calculate sunset time for.
    latitude : FLOAT
        Latitude at which to calculate sunset time.
    longitude : FLOAT
        Longitude at which to calculate sunset time.

    Returns
    -------
    datetime.datetime object
        Time to the nearest 15 minutes that the Sun will set
        below the horizon for the specified day at the specified
        coordinates.

    '''
    if type(day) is not datetime.datetime:
        day = time_utils.convert_to_datetime(day)
    for i in range(12*4):
        hour = int(i/4) + 12
        minute = 15*(i % 4)
        time = datetime.datetime(day.year, day.month, day.day, hour, minute, 0, tzinfo=day.tzinfo)
        alt = get_sun_elevation(time, latitude, longitude)
        if alt <= 0:
            return time.replace(tzinfo=datetime.timezone.utc) - time.utcoffset()