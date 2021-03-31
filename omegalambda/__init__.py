from .main.common.datatype.filter_wheel import *
from .main.common.datatype.observation_ticket import *
from .main.common.datatype.object_reader import *
from .main.common.IO.config_reader import *
from .main.common.IO.json_reader import *
from .main.common.util import time_utils as time
from .main.common.util import filereader_utils as file
from .main.common.util import conversion_utils as conversion
from .main.controller.camera import *
from .main.controller.dome import *
from .main.controller.flatfield_lamp import *
from .main.controller.focuser_control import *
from .main.controller.hardware import *
from .main.controller.telescope import *
from .main.controller.thread_monitor import *
from .main.drivers.driver import *
from .main.observing.calibration import *
from .main.observing.condition_checker import *
from .main.observing.guider import *
from .main.observing.observation_run import *

import os
__file = os.path.abspath(os.path.dirname(__file__))
__filereader = Reader(os.path.join(__file, r'config', r'parameters_config.json'))
__objreader = ObjectReader(__filereader)

del os, __file, __filereader, __objreader

__version__ = "1.2.3"
__author__ = ['Michael Reefe', 'Owen Alfaro', 'Shawn Foster']
__credits__ = ['GMU Observatory', 'Peter Plavchan', 'GMU Exoplaneteers Research Group']