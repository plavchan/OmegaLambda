from main.observing.observation_run import ObservationRun
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader
import datetime
import os
import logging

logging.basicConfig(level=logging.DEBUG, format='(%(threadName)-10s) %(message)s',)

try: global_config = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))
except: print('ERROR: Error initializing global config object')

folder = datetime.datetime.now().strftime('%Y%m%d')
try: os.mkdir(os.path.join(global_config.ticket.data_directory, folder))
except: print('ERROR: Could not create directory, or directory already exists')
else: print('New directory for tonight\'s observing has been made!')

try: json_reader = Reader(os.path.join(global_config.ticket.ticket_directory, 'test.json'))
except: print('ERROR: Could not read observation ticket.')
else: pass

try: global_filter = ObjectReader(Reader(os.path.join(global_config.ticket.config_directory, 'fw_config.json')))
except: print('ERROR: Error initializing global filter object')

try: object_reader = ObjectReader(json_reader)
except: print('ERROR: Could not read observation ticket.')
else: print('Observation ticket has been read.')

run_object = ObservationRun([object_reader.ticket],
                            os.path.join(global_config.ticket.data_directory, folder))
run_object.observe()