#Hardware class to be inherited by camera, telescope, dome, etc.

import threading
import queue
import time
import logging
import pythoncom
import win32com.client
from main.common.IO import config_reader

class Hardware(threading.Thread):
    
    def __init__(self, name, loop_time = 1.0/60):
        self.q = queue.Queue()
        self.timeout = loop_time
        self.running = True
        self.label = name
        super(Hardware, self).__init__(name = self.label + '-Th')
        
        self.config_dict = config_reader.get_config()
        self.live_connection = threading.Event()
        
        
    def onThread(self, function, *args, **kwargs):
        self.q.put((function, args, kwargs))
        
    def run(self):
        pythoncom.CoInitialize()
        dispatch_dict = {'Camera': 'MaxIm.CCDCamera', 'Telescope': 'ASCOM.SoftwareBisque.Telescope', 'Dome': 'ASCOMDome.Dome'}
        if self.label in dispatch_dict:
            COMobj = win32com.client.Dispatch(dispatch_dict[self.label])
        if self.label == 'Camera':
            self.Camera = COMobj
            self.Application = win32com.client.Dispatch("MaxIm.Application")
            self.check_connection()
            self.Camera.DisableAutoShutdown = True
            self.Camera.AutoDownload = True
            self.Application.LockApp = True
            self.coolerSet(True)
        elif self.label == 'Telescope':
            self.Telescope = COMobj
            self.Telescope.SlewSettleTime = 1
            self.check_connection()
        elif self.label == 'Dome':
            self.Dome = COMobj
            self.check_connection()
        else:
            print("ERROR: Invalid hardware name")
        while self.running:
            logging.debug("{0:s} thread is alive".format(self.label))
            try:
                function, args, kwargs = self.q.get(timeout=self.timeout)
                function(*args, **kwargs)
            except queue.Empty:
                time.sleep(1)
        pythoncom.CoUninitialize()
        
    def stop(self):
        logging.debug("Stopping {} thread".format(self.label))
        self.running = False
        
    def check_connection(self):
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