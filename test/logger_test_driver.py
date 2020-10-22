import logging

from ..logger.logger import Logger

log = Logger(r'C:/Users/GMU Observtory1/-omegalambda/config/logging.json')

for i in range(1000000):
    logging.debug('This is a logger test, filling random data.')

logging.debug('Logging test over')
