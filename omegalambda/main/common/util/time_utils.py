import datetime
from astropy.time import Time
from barycorrpy import JDUTC_to_BJDTDB
import logging
from typing import Union, Optional

import pytz
import dateutil.parser


def rounddown_300(x: Union[int, float]) -> int:
    """

    Parameters
    ----------
    x : INT or FLOAT
        Any real number.

    Returns
    -------
    INT
        Rounds x down to the nearest multiple of 300.
        Does not round up.  Needed for weather.com api.

    """
    logging.debug('Called time_utils function')
    return int(x/300)*300


def convert_to_datetime_utc(date: str) -> datetime.datetime:
    """

    Parameters
    ----------
    date : STR
        May be a date/time string in almost any format.  Will be parsed by dateutil.parser.

    Returns
    -------
    DATETIME.DATETIME
        Datetime object in UTC time, timezone-aware.

    """
    logging.debug('Called time_utils function')
    d = dateutil.parser.parse(date)
    return d.replace(tzinfo=pytz.UTC) - d.utcoffset()


def convert_to_datetime(date: str) -> datetime.datetime:
    """

    Parameters
    ----------
    date : STR
        May be a date/time string in almost any format.  Will be parsed by dateutil.parser.

    Returns
    -------
    d : DATETIME.DATETIME
        Datetime object in whatever timezone is passed in, timezone-aware.

    """
    logging.debug('Called time_utils function')
    d = dateutil.parser.parse(date)
    return d


def datetime_to_epoch_milli_converter(date: Union[str, datetime.datetime]) -> Union[int, float]:
    """

    Parameters
    ----------
    date : DATETIME.DATETIME
        Should be timezone-aware, in UTC--generated from convert_to_datetime_UTC.

    Returns
    -------
    FLOAT
        Number of milliseconds since Jan. 1, 1970.  Common way of measuring time.

    """
    logging.debug('Called time_utils function')
    if type(date) is not datetime.datetime:
        date = convert_to_datetime_utc(date)
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (date.replace(tzinfo=None) - epoch).total_seconds() * 1000


def epoch_milli_to_datetime_converter(epochmilli: Union[int, float]) -> datetime.datetime:
    """

    Parameters
    ----------
    epochmilli : FLOAT
        Timestamp in the form of milliseconds since Jan. 1, 1970.

    Returns
    -------
    DATETIME.DATETIME
        Timezone-aware, UTC datetime.datetime object.

    """
    logging.debug('Called time_utils function')
    return datetime.datetime.utcfromtimestamp(epochmilli / 1000).replace(tzinfo=pytz.UTC)


def days_since_j2000(date: Optional[Union[datetime.datetime, str]] = None) -> float:
    """

    Parameters
    ----------
    date : DATETIME.DATETIME, optional
        Should be timezone-aware, UTC datetime.datetime object.  The default is None, which
        will calculate the days since J2000 for today.

    Returns
    -------
    days : FLOAT
        Timestamp in the form of days since Jan. 1, 2000.

    """
    logging.debug('Called time_utils function')
    if date is None:
        date = datetime.datetime.now(datetime.timezone.utc)
    if type(date) is not datetime.datetime:
        date = convert_to_datetime_utc(date)
    j2000 = datetime.datetime(2000, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    days = (date - j2000).total_seconds()/(60*60*24)
    return days


def days_of_year(date: Optional[Union[str, datetime.datetime]] = None) -> float:
    """

    Parameters
    ----------
    date : DATETIME.DATETIME, optional
        Should be timezone-aware datetime object. The default is None, which will calculate the
        days of the year for today.

    Returns
    -------
    days : FLOAT
        Timestamp in the form of days since Jan. 1, [current year].

    """
    logging.debug('Called time_utils function')
    if date is None:
        date = datetime.datetime.now(datetime.timezone.utc)
    if type(date) is not datetime.datetime:
        date = convert_to_datetime_utc(date)
    first_day = datetime.datetime(date.year, 1, 1, 0, 0, 0, tzinfo=date.tzinfo)
    days = (date - first_day).total_seconds()/(60*60*24)
    return days + 1


def fractional_hours_of_day(time: Optional[Union[str, datetime.datetime]] = None) -> float:
    """

    Parameters
    ----------
    time : DATETIME.DATETIME, optional
        Should be timezone-aware, UTC datetime.datetime object.  The default is None, which
        will calculate the fractional hours of the day for right now.

    Returns
    -------
    hours : FLOAT
        Timestamp in the form of fractional hours of the day.  I.e. if it is 12 p.m., the day
        is halfway over, so this will return 0.5.

    """
    logging.debug('Called time_utils function')
    if time is None:
        time = datetime.datetime.now(datetime.timezone.utc)
    if type(time) is not datetime.datetime:
        time = convert_to_datetime_utc(time)
    hours = (time - datetime.datetime(time.year, time.month, time.day, 0, 0, 0, tzinfo=datetime.timezone.utc))
    hours = hours.total_seconds()/(60*60)
    return hours


def decimal_year(time=None) -> float:
    """

    Returns
    -------
    FLOAT
        Current year in decimal form.  i.e. if it is June, 1995, this would return 1995.5.
        Needed for different epoch coordinate conversions.

    """
    logging.debug('Called time_utils function')
    if time is None:
        time = datetime.datetime.now()
    mods = ((time.year % 400 == 0), (time.year % 100 == 0), (time.year % 4 == 0))
    leap = True if mods[0] else False if mods[1] else True if mods[2] else False
    days_in_year = 365 if not leap else 366
    return time.year + (time.month - 1)/12 + (time.day - 1)/days_in_year + time.hour/(days_in_year*24) + \
        time.minute/(days_in_year*24*60) + time.second/(days_in_year*24*60*60)


def get_local_sidereal_time(longitude: float, date: Optional[Union[str, datetime.datetime]] = None) -> float:
    """

    Parameters
    ----------
    longitude : FLOAT
        Site longitude where you want to calculate LST.  West is negative.
    date : DATETIME.DATETIME, optional
        Date and time for which you want to calculate LST. The default is None, which
        will calculate the LST for the current date & time.

    Returns
    -------
    LST : FLOAT
        Local sidereal time in hours.

    """
    logging.debug('Called time_utils function')
    if date is None:
        date = datetime.datetime.now(datetime.timezone.utc)
    if type(date) is not datetime.datetime:
        date = convert_to_datetime_utc(date)
    date = convert_to_jd_utc(date)
    tmid = (date - 2451545.0) / 36525.0
    # gmst in seconds
    gmst = 280.46061837 + 360.98564736629 * 36525.0 * tmid + 0.000387933 * (tmid**2) - (tmid**3) / 38710000
    gmst = (gmst % 360)
    lmst = (gmst + longitude)/15 % 24
    return lmst


def convert_to_jd_utc(time=None):
    if not time:
        time = datetime.datetime.now(datetime.timezone.utc)
    if type(time) is not datetime.datetime:
        time = convert_to_datetime_utc(time)
    t = Time(time, format='datetime', scale='utc')
    return t.jd


def convert_to_bjd_tdb(jd, starname, lat, lon, height):
    # J2000 coords
    return JDUTC_to_BJDTDB(JDUTC=jd, starname=starname, leap_update=False, lat=lat, longi=lon, alt=height)[0]