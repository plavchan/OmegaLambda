# Hardware class to be inherited by camera, telescope, dome, etc.
import threading
import queue
import time
import logging

import pythoncom
import win32com.client

from ..common.IO import config_reader


class Hardware(threading.Thread):

    timeout = 1.0/60

    def __init__(self, name):
        """
        Initializes hardware as a subclass of threading.Thread.

        Parameters
        ----------
        name : STR
            Details the name of the hardware object.  Important for naming the thread
            and calling the correct dispatch functions.

        Returns
        -------
        None.

        """
        self.q = queue.Queue()
        self.label = name
        self.stopping = threading.Event()
        self.crashed = threading.Event()
        self.Camera = None
        self.Application = None
        self.Telescope = None
        self.Dome = None
        self.Focuser = None
        self.ser = None
        super(Hardware, self).__init__(name=self.label + '-Th', daemon=True)       # Called threading.Thread.__init__

        self.config_dict = config_reader.get_config()  # Gets the config object as a class variable
        self.live_connection = threading.Event()

    def onThread(self, function, *args, **kwargs):
        """
        Description
        -----------
        Used to put a function on a specific thread other than the main thread.  This will put said function
        on that thread's queue and will be called as soon as the thread is ready to receive such a request.  Threads
        check for new function calls once every second when they are not already running a function.

        Parameters
        ----------
        function : BOUND METHOD
            A class method that is to be put in the thread queue and called on the
            appropriate thread.
        *args : ANY
            The arguments to be passed to the class method.
        **kwargs : ANY
            The keyword arguments to be passed to the class method.

        Returns
        -------
        None.

        """
        self.q.put((function, args, kwargs))
        logging.debug('A class method has been put on the {} queue'.format(self.label))

    def _choose_type(self):
        """
        Description
        -----------
        Chooses the correct COM object to dispatch based on the hardware class name.

        Returns
        -------
        check : BOOL
            True if the hardware could find the correct object to connect to, otherwise False.

        """
        dispatch_dict = {'Camera': 'MaxIm.CCDCamera', 'Telescope': 'ASCOM.SoftwareBisque.Telescope',
                         'Dome': 'ASCOMDome.Dome', 'Focuser': 'RoboFocus.FocusControl'}
        chosen = True
        if self.label in dispatch_dict:
            comobj = win32com.client.Dispatch(dispatch_dict[self.label])
        else:
            comobj = None
        if self.label == 'Camera':
            self.Camera = comobj
            self.Application = win32com.client.Dispatch("MaxIm.Application")
            self.check_connection()
            self.Camera.DisableAutoShutdown = True
            # Setting basic configurations for the camera
            self.Camera.AutoDownload = True
            self.Application.LockApp = True
            self.cooler_set(True)
            # Starts the camera's cooler--method defined in camera.py
        elif self.label == 'Telescope':
            self.Telescope = comobj
            self.Telescope.SlewSettleTime = 1
            self.check_connection()
        elif self.label == 'Dome':
            self.Dome = comobj
            self.check_connection()
        elif self.label == 'Focuser':
            self.Focuser = comobj
            self.check_connection()
        elif self.label == 'FlatLamp':
            self.check_connection()
        elif self.label in ('Guider', 'Calibration', 'FocusProcedures'):
            pass
        else:
            logging.error("Invalid hardware name")
            chosen = False
        return chosen

    def run(self):
        """
        Description
        -----------
        Started by calling Hardware.start() [as a subclass of threading.Thread].
        Creates a hardware-specific thread for the camera, telescope, or dome that dispatches the
        correct COM object and starts a loop that continuously checks the queue to see if any
        function calls have been passed via onThread.

        Only stops once self.running has been set to False by calling self.stop.

        Returns
        -------
        None.

        """
        pythoncom.CoInitialize()
        check = self._choose_type()
        if not check:
            pythoncom.CoUninitialize()
            return
        while not self.stopping.isSet():
            logging.debug("{0:s} thread is alive".format(self.label))
            try:
                function, args, kwargs = self.q.get(timeout=self.timeout)
                function(*args, **kwargs)
                logging.debug('{} has been run on the {} thread'.format(function, self.label))
            except queue.Empty:
                time.sleep(1)
        pythoncom.CoUninitialize()
        
    def stop(self):
        """
        Description
        -----------
        Sets self.running to False, which stops the run method from executing.
        Should be called via onThread, otherwise a thread may be stopped before it can finish executing a previous
        function call.

        Returns
        -------
        None.

        """
        logging.debug("Stopping {} thread".format(self.label))
        self.stopping.set()
        
    def check_connection(self):
        """
        Description
        -----------
        Depending on which type of hardware, this will check if it has been properly connected
        or not from the dispatch commands.  It is overriden by most child classes of hardware.

        Returns
        -------
        None.

        """
        logging.info('Checking connection for the {}'.format(self.label))
        print("Invalid hardware type to check connection for: {}".format(self.label))

    def cooler_set(self, toggle):
        """
        Description
        -----------
        Purposefully left empty to be overriden by Camera subclass.

        """
        print("Invalid hardware to set the cooler for: {}".format(self.label))

    @classmethod
    def new_loop_time(cls, loop_time):
        """
        Description
        -----------
        Resets the Hardware loop time to the specified value for all Hardware classes.

        Parameters
        ----------
        loop_time : INT or FLOAT
            How quickly the queue will loop and check for new functions to execute, in seconds.

        Returns
        -------
        None

        """
        cls.timeout = loop_time
