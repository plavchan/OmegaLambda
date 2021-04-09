import numpy as np
import datetime
from typing import Tuple, Union, Optional

from astropy import units as u
from astropy.coordinates import SkyCoord, FK5, AltAz, get_sun, EarthLocation
from astropy.time import Time

from . import time_utils


def get_decha_from_altaz(azimuth: float, altitude: float, latitude: float) -> Tuple[float, float]:
    """
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
    """
    (azimuth_r, altitude_r, latitude_r) = np.radians([azimuth, altitude, latitude])
    dec_r = np.arcsin(np.sin(altitude_r)*np.sin(latitude_r)
                      + np.cos(altitude_r)*np.cos(latitude_r)*np.cos(azimuth_r))
    ha_r = np.arccos((np.sin(altitude_r)
                      - np.sin(latitude_r)*np.sin(dec_r))/(np.cos(latitude_r)*np.cos(dec_r)))
    if np.sin(azimuth_r) > 0:
        ha_r = 2*np.pi - ha_r
    (dec, HA) = np.degrees([dec_r, ha_r])
    return dec, HA


def convert_altaz_to_radec(azimuth: float, altitude: float, latitude: float, longitude: float,
                           time: datetime.datetime) -> Tuple[float, float]:
    """
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
    """
    lst = time_utils.get_local_sidereal_time(longitude, time)
    lst *= 15
    (dec, HA) = get_decha_from_altaz(azimuth, altitude, latitude)
    ra = (lst - HA)/15
    while ra < 0:
        ra += 24
    while ra > 24:
        ra -= 24
    return ra, dec


def convert_radec_to_altaz(ra: float, dec: float, latitude: float, longitude: float,
                           time: datetime.datetime, leap_seconds: float = 0, refraction=True) -> Tuple[float, float]:
    """
    Parameters
    ----------
    ra : FLOAT
        Given right ascension of target.
    dec : FLOAT
        Given declination of target.
    latitude : FLOAT
        Latitude of observatory.
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
    """
    lst = time_utils.get_local_sidereal_time(longitude, time, leap_seconds)
    ha = (lst - ra) % 24
    if ha > 12:
        ha -= 24
    # Convert to degrees
    ha *= 15
    (dec_r, latitude_r, longitude_r, HA_r) = np.radians([dec, latitude, longitude, ha])

    alt_r = np.arcsin(np.sin(dec_r)*np.sin(latitude_r)+np.cos(dec_r)*np.cos(latitude_r)*np.cos(HA_r))
    az_r = np.arctan2(-np.cos(dec_r)*np.sin(HA_r), np.sin(dec_r)*np.cos(latitude_r)-np.sin(latitude_r)*np.cos(dec_r)*np.cos(HA_r))
    (az, alt) = np.degrees([az_r, alt_r])
    az = az % 360

    if refraction:
        pressure = 760
        temperature = 10
        if alt >= 15.0:
            arg = (90.0 - alt) * np.pi/180
        elif alt >= 0.0:
            arg = (90.0 - 15.0) * np.pi/180
        else:
            return az, alt
        dalt = np.tan(arg)
        dalt = 58.276 * dalt - 0.0824 * dalt**3
        dalt /= 3600.
        dalt = dalt * (pressure / 760.) * (283. / (273. + temperature))
        alt += dalt

    return az, alt


def convert_j2000_to_apparent(ra: float, dec: float) -> Tuple[float, float]:
    """
    Parameters
    ----------
    ra : FLOAT
        Right ascension to be converted from J2000 coordinates to apparent
        coordinates.
    dec : FLOAT
        Declination to be converted from J2000 coordinates to apparent coordinates.

    Returns
    -------
    coords_apparent.ra.hour: FLOAT
        Right ascension of target in local topocentric coordinates ("JNow").
    coords_apparent.dec.degree: FLOAT
        Declination of target in local topocentric coordinates ("JNow").
    """
    year = time_utils.decimal_year()
    coords_j2000 = SkyCoord(ra=ra*u.hourangle, dec=dec*u.degree, frame='icrs')
    # ICRS Equinox is always J2000
    coords_apparent = coords_j2000.transform_to(FK5(equinox='J{}'.format(year)))
    return coords_apparent.ra.hour, coords_apparent.dec.degree


def convert_apparent_to_j2000(ra: float, dec: float) -> Tuple[float, float]:
    """
    Parameters
    ----------
    ra : FLOAT
        Right ascension to be converted from apparent to J2000 coordinates.
        coordinates.
    dec : FLOAT
        Declination to be converted from apparent to J2000 coordinates.

    Returns
    -------
    coords_j2000.ra.hour: FLOAT
        Right ascension of target in J2000.
    coords_j2000.dec.degree: FLOAT
        Declination of target in J2000.
    """
    year = time_utils.decimal_year()
    coords_apparent = SkyCoord(ra=ra*u.hourangle, dec=dec*u.degree, frame=FK5(equinox='J{}'.format(year)))
    # ICRS Equinox is always J2000
    coords_j2000 = coords_apparent.transform_to('icrs')
    return coords_j2000.ra.hour, coords_j2000.dec.degree


def get_sun_elevation(time: Union[str, datetime.datetime], latitude: float, longitude: float) -> float:
    """
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

    """
    if type(time) is not datetime.datetime:
        time = time_utils.convert_to_datetime_utc(time)
    astrotime = Time(time, format='datetime', scale='utc')
    coords = get_sun(astrotime)
    (az, alt) = convert_radec_to_altaz(float(coords.ra.hour), float(coords.dec.degree), latitude, longitude, time)
    return alt


def get_sunset(day: Union[str, datetime.datetime], latitude: float, longitude: float) -> Optional[datetime.datetime]:
    """
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

    """
    if type(day) is not datetime.datetime:
        day = time_utils.convert_to_datetime(day)
    for i in range(12*4):
        hour = int(i/4) + 12
        minute = 15*(i % 4)
        time = datetime.datetime(day.year, day.month, day.day, hour, minute, 0, tzinfo=day.tzinfo)
        alt = get_sun_elevation(time, latitude, longitude)
        if alt <= 0:
            return time.replace(tzinfo=datetime.timezone.utc) - time.utcoffset()


def airmass(altitude: float) -> float:
    return 1/np.cos(np.pi/2 - np.radians(altitude))


def sexagesimal(decimal):
    hh = int(decimal)
    f1 = hh if hh != 0 else 1

    extra = decimal % f1
    mm = int(extra * 60)
    f2 = mm if mm != 0 else 1

    extra2 = (extra * 60) % f2
    ss = extra2 * 60

    mm = abs(mm)
    ss = abs(ss)
    return '{:02d} {:02d} {:08.5f}'.format(hh, mm, ss)