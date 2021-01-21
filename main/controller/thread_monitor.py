import time
import logging
import threading


class Monitor(threading.Thread):
    def __init__(self):
        self.run_th_monitor = True
        self.threadcrash = threading.Event()
        self.crashed = []
        super(Monitor, self).__init__(name='Monitor')

    def run(self, threadlist):
        '''
        Description
        -----------
        Constantly checks the inputted threads to see if they
        are alive

        Parameters
        ----------
        threadlist : DICT
            List of thread handles
        Returns
        -------
        None.
        '''
        logging.info('Beginning thread monitoring')
        while self.run_th_monitor:
            for th_name in threadlist.keys():
                if not threadlist[th_name].is_alive():
                    if not threadlist[th_name].name in self.crashed:
                        self.crashed.append(threadlist[th_name].name)
                        logging.error('{} thread has raised an exception'.format(threadlist[th_name].name))
                    self.threadcrash.set()





