from main.observing.observation_run import ObservationRun
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader
import datetime
import os


folder = (datetime.datetime.now(datetime.timezone.utc)).strftime('%Y%m%d')
try: os.mkdir(r'h:\observatory files\observing sessions\2020_data\{0:s}'.format(folder))
except: print('ERROR: Could not create directory')
else: print('New directory for tonight\'s observing has been made!')

try: json_reader = Reader(r'c:\users\gmu observtory1\-omegalambda\resources\test.json')
except: print('ERROR: Error reading observation ticket')

try: object_reader = ObjectReader(json_reader)
except: print('ERROR: Error reading observation ticket')
else: print('Observation ticket has been read.  Starting observation run!')

run_object = ObservationRun([object_reader.ticket], r'h:\observatory files\observing sessions\2020_data\{0:s}'.format(folder))
run_object.observe()

