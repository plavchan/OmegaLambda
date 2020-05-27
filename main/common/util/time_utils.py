import datetime
import pytz
import dateutil.parser

def convert_to_datetime_UTC(date):
    d = dateutil.parser.parse(date)
    return d.replace(tzinfo=pytz.UTC) - d.utcoffset()

def datetime_to_epoch_milli_converter(date):
    if type(date) is not datetime.datetime:
        date = convert_to_datetime_UTC(date)
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (date.replace(tzinfo=None) - epoch).total_seconds() * 1000

def epoch_milli_to_datetime_converter(epochmilli):
    return datetime.datetime.utcfromtimestamp(epochmilli / 1000).replace(tzinfo=pytz.UTC)

def days_since_j2000(date):
    if type(date) is not datetime.datetime:
        date = convert_to_datetime_UTC(date)
    if date == None:
        date = datetime.datetime.now(datetime.timezone.utc)
    j2000 = datetime.datetime(2000, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    days = (date - j2000).total_seconds()/(60*60*24)
    return days

def fractional_hours_of_day(time):
    if type(time) is not datetime.datetime:
        time = convert_to_datetime_UTC(time)
    if time == None:
        time = datetime.datetime.now(datetime.timezone.utc)
    hours = (time - datetime.datetime(time.year, time.month, time.day, 0, 0, 0, tzinfo=datetime.timezone.utc))
    hours = hours.total_seconds()/(60*60)
    return hours

def get_local_sidereal_time(longitude, date=None):
    if date == None:
        date = datetime.datetime.now(datetime.timezone.utc)
    if type(date) is not datetime.datetime:
        date = convert_to_datetime_UTC(date)
    days = days_since_j2000(date)
    hours = fractional_hours_of_day(date)
    LST = 100.46 + 0.985647*days + 15*hours + longitude
    while LST > 360:
        LST -= 360
    while LST < 0:
        LST += 360
    LST = LST/15
    return LST

