import time
import logging
import threading


class Monitor(threading.Thread):
    def __init__(self):
        self.runthemonitor = True
        self.threadcrash = threading.Event()
        self.crashed = []
        super(Monitor, self).__init__(name='Monitor')

    def monitor_run(self, threadlist):
        '''
        Description
        -----------
        Constantly checks the inputted threads to see if they
        are alive

        Parameters
        ----------
        threadlist : LIST
            List of thread handles
        Returns
        -------
        None.
        '''
        logging.info('Beginning thread monitoring')
        while self.runthemonitor:
            for threadname in threadlist:
                if not threadname.is_alive():
                    logging.error('{} thread has raised an exception'.format(threadname.name))
                    if not threadname.name in self.crashed:
                        self.crashed.append(threadname.name)
                    self.threadcrash

    def crash_return(self):
        '''
        Description
        -----------
        Returns the crashed thread list created in monitor_run

        Returns
        -------
        self.crashed: LIST
            list of crashed threads to be restarted
        '''
        return self.crashed




