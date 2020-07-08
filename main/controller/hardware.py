#Hardware class to be inherited by camera, telescope, dome, etc.
import threading
import queue
import time
import logging

import pythoncom
import win32com.client

from ..common.IO import config_reader

class Hardware(threading.Thread):           #Subclassed from threading.Thread
    
    def __init__(self, name, loop_time = 1.0/60):
        '''

        Parameters
        ----------
        name : STR
            Details the name of the hardware object.  Important for naming the thread
            and calling the correct dispatch functions.
        loop_time : FLOAT, optional
            The time that the queue will wait for a function call before cycling on. The default is 1.0/60.

        Returns
        -------
        None.

        '''
        self.q = queue.Queue()
        self.timeout = loop_time
        self.label = name
        self.stopping = threading.Event()
        self.crashed = threading.Event()
        super(Hardware, self).__init__(name = self.label + '-Th')               #Called threading.Thread.__init__ 
        
        self.config_dict = config_reader.get_config()                           #Gets the global config object
        self.live_connection = threading.Event()
        
        
    def onThread(self, function, *args, **kwargs):
        '''

        Parameters
        ----------
        function : FUNCTION
            A class method that is to be put in the thread queue and called on the
            appropriate thread.
        *args : ANY TYPE
            The arguments to be passed to the class method.
        **kwargs : ANY TYPE
            The keyword arguments to be passed to the class method.

        Returns
        -------
        None.

        '''
        self.q.put((function, args, kwargs))
        logging.debug('A class method has been put on the {} queue'.format(self.label))
        
    def run(self):
        '''
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

        '''
        pythoncom.CoInitialize()
        dispatch_dict = {'Camera': 'MaxIm.CCDCamera', 'Telescope': 'ASCOM.SoftwareBisque.Telescope', 
                         'Dome': 'ASCOMDome.Dome', 'Focuser': 'RoboFocus.FocusControl'}
        if self.label in dispatch_dict:
            COMobj = win32com.client.Dispatch(dispatch_dict[self.label])
        if self.label == 'Camera':
            self.Camera = COMobj
            self.Application = win32com.client.Dispatch("MaxIm.Application")
            self.check_connection()
            self.Camera.DisableAutoShutdown = True                          # Setting basic configurations for the camera
            self.Camera.AutoDownload = True
            self.Application.LockApp = True
            self.coolerSet(True)                                            # Starts the camera's cooler--method defined in camera.py
        elif self.label == 'Telescope':
            self.Telescope = COMobj
            self.Telescope.SlewSettleTime = 1
            self.check_connection()
        elif self.label == 'Dome':
            self.Dome = COMobj
            self.check_connection()
        elif self.label == 'Focuser':
            self.Focuser = COMobj
            self.check_connection()
        elif self.label == 'FlatLamp':
            self.check_connection()
        elif self.label == 'FocusProcedures' or self.label == 'Guider':
            pass
        else:
            logging.error("Invalid hardware name")
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
        '''
        Description
        -----------
        Sets self.running to False, which stops the run method from executing.
        Must be called via onThread.

        Returns
        -------
        None.

        '''
        logging.debug("Stopping {} thread".format(self.label))
        self.stopping.set()
        
    def check_connection(self):
        '''
        Description
        -----------
        Depending on which type of hardware, this will check if it has been properly connected
        or not from the dispatch commands.

        Returns
        -------
        None.

        '''
        logging.info('Checking connection for the {}'.format(self.label))
        self.live_connection.clear()
        if self.label == 'Camera':
            if self.Camera.LinkEnabled:
                print("Camera is already connected")
            else:
                try: 
                    self.Camera.LinkEnabled = True
                    self.live_connection.set()
                except: print("ERROR: Could not connect to camera")
                else: print("Camera has successfully connected") 
        elif self.label == 'Telescope':
            if not self.Telescope.Connected:
                try: 
                    self.Telescope.Connected = True
                    self.live_connection.set()
                except: print("ERROR: Could not connect to the telescope")
                else: print("Telescope has successfully connected")
            else: print("Already connected")
        elif self.label == 'Dome':
            try: 
                self.Dome.Connected = True
                self.live_connection.set()
            except: print("ERROR: Could not connect to dome")
            else: print("Dome has successfully connected")
        elif self.label == 'FlatLamp':
            try: self.ser.open()
            except: print("ERROR: Flatfield lamp did not connect successfully.")
            else: print("Flatfield Lamp has successfully connected")
        elif self.label == 'Focuser':
            self.Focuser.actOpenComm()
            time.sleep(2)
            if self.Focuser.getCommStatus():
                print("Focuser has successfully connected")
                self.live_connection.set()
            else:
                print("ERROR: Could not connect to focuser")
        else:
            print("Invalid hardware type to check connection for")