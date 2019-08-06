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

