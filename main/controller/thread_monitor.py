import time
import logging
import threading


class Monitor(threading.Thread):
    def __init__(self):
        self.runthemonitor = True
        self.threadcrash = threading.Event()
        super(Monitor, self).__init__(name='Monitor')

    def monitor_run(self, threadlist):
        logging.info('Beginning thread monitoring')
        v = threading.Thread(target=self.count(), name='counting')
        v.start()

        while self.runthemonitor:
            for threadname in threadlist:
                if not threadname.is_alive():
                    logging.error('{} thread has raised an exception'.format(threadname.name))
                    self.threadcrash
            time.sleep(2)

    def count(self):
        x = 0
        while x <= 45:
            time.sleep(1)
            x += 1
        self.runthemonitor = False




