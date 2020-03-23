from main.observing.observation_run import ObservationRun
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader
import datetime
import os


folder = (datetime.datetime.now(datetime.timezone.utc)).strftime('%Y%m%d')
try: os.mkdir(r'h:\observatory files\observing sessions\2020_data\{0:s}'.format(folder))
except: print('ERROR: Could not create directory')

json_reader = Reader(r'c:\users\gmu observtory1\-omegalambda\resources\test.json')
object_reader = ObjectReader(json_reader)

run_object = ObservationRun([object_reader.ticket], r'h:\observatory files\observing sessions\2020_data\{0:s}'.format(folder))
