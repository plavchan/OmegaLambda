import time
import logging
import threading



class Monitor(threading.Thread):
    def __init__(self):
        self.run_th_monitor = True
        self.threadcrash = threading.Event()
        self.crashed = []
        self.n_restarts = {'camera': 0, 'telescope': 0,'dome': 0, 'focuser': 0,
                           'flatlamp': 0,'Conditions-Th': 0, 'guider': 0,
                           }
        super(Monitor, self).__init__(name='Monitor')

    def run(self):
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


    def pass_dict(self, th_dict):
        global threadlist
        threadlist = th_dict



