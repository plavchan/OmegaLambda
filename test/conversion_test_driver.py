# Conversion utils tester
import datetime
from ..main.common.util import conversion_utils

test = conversion_utils.get_sunset('2020-07-01 12:00:00-0400', 38.828, -77.305)
print(test)