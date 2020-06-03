from main.observing.observation_run import ObservationRun
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader
import datetime
import os
import logging

logging.basicConfig(level=logging.DEBUG, format='(%(threadName)-10s) %(message)s',)


folder = datetime.datetime.now().strftime('%Y%m%d')
try: os.mkdir(r'h:\observatory files\observing sessions\2020_data\{0:s}'.format(folder))
except: print('ERROR: Could not create directory, or directory already exists')
else: print('New directory for tonight\'s observing has been made!')

try: json_reader = Reader(r'c:\users\gmu observtory1\-omegalambda\test\test.json')
except: print('ERROR: Could not read observation ticket.')
else: pass

try: global_filter = ObjectReader(Reader(r'c:\users\gmu observtory1\-omegalambda\config\fw_config.json'))
except: print('ERROR: Error initializing global filter object')

try: global_config = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))
except: print('ERROR: Error initializing global config object')

try: object_reader = ObjectReader(json_reader)
except: print('ERROR: Could not read observation ticket.')
else: print('Observation ticket has been read.')

run_object = ObservationRun([object_reader.ticket],
                            r'h:\observatory files\observing sessions\2020_data\{0:s}'.format(folder))
run_object.observe()
