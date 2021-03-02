import time
import logging
import threading



class Monitor(threading.Thread):
    def __init__(self, th_dict):
        self.threadlist = th_dict
        self.run_th_monitor = True
        self.crashed = []
        self.n_restarts = {'camera': 0, 'telescope': 0,'dome': 0, 'focuser': 0,
                           'flatlamp': 0,'conditions': 0, 'guider': 0,
                           'focus_procedures': 0, 'gui': 0
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
        logging.debug('Beginning thread monitoring')
        while self.run_th_monitor:
            for th_name in self.threadlist.keys():
                if not self.threadlist[th_name].is_alive():
                    if not self.threadlist[th_name].name in self.crashed:
                        self.crashed.append(th_name)
                        logging.error('{} thread has raised an exception'.format(self.threadlist[th_name].name))
                    time.sleep(15)




