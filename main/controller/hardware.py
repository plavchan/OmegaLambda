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
        super(Hardware, self).__init__(name=name)
        
        self.config_dict = config_reader.get_config()
        
    def onThread(self, function, *args, **kwargs):
        self.q.put((function, args, kwargs))
        
    def run(self, name):
        pythoncom.CoInitialize()
        dispatch_dict = {'Camera': 'MaxIm.CCDCamera', 'Telescope': 'ASCOM.SoftwareBisque.Telescope', 'Dome': 'ASCOMDome.Dome'}
        COMobj = win32com.client.Dispatch(dispatch_dict[name])
        if name == 'Camera':
            self.Camera = COMobj
            self.Application = win32com.client.Dispatch("MaxIm.Application")
            self.check_connection(name)
            self.Camera.DisableAutoShutdown = True
            self.Camera.AutoDownload = True
            self.Application.LockApp = True
            self.coolerset(True)
        elif name == 'Telescope':
            self.Telescope = COMobj
            self.Telescope.SlewSettleTime = 1
            self.check_connection(name)
        elif name == 'Dome':
            self.Dome = COMobj
            self.check_connection(name)
        else:
            print("ERROR: Invalid hardware name")
        while self.running:
            logging.debug("{0:s} thread is alive".format(name))
            try:
                function, args, kwargs = self.q.get(timeout=self.timeout)
                function(*args, **kwargs)
            except queue.Empty:
                time.sleep(1)
        pythoncom.CoUninitialize()
        
    def check_connection(self, name):
        if name == 'Camera':
            if self.Camera.LinkEnabled:
                print("Camera is already connected")
            else:
                try: 
                    self.Camera.LinkEnabled = True
                except: print("ERROR: Could not connect to camera")
                else: print("Camera has successfully connected") 
        elif name == 'Telescope':
            if not self.Telescope.Connected:
                try: 
                    self.Telescope.Connected = True
                except: print("ERROR: Could not connect to the telescope")
                else: print("Telescope has successfully connected")
            else: print("Already connected")
        elif name == 'Dome':
            try: self.Dome.Connected = True
            except: print("ERROR: Could not connect to dome")
            else: print("Dome has successfully connected")
            
    def coolerSet(self, toggle):
        try: self.Camera.CoolerOn = True
        except: print("ERROR: Could not turn on cooler")
        
        if self.Camera.CoolerOn and toggle == True:
            try: self.Camera.TemperatureSetpoint = self.config_dict.cooler_setpoint
            except: pass
            else: print("Cooler Setpoint set to {0:.1f} C".format(self.Camera.TemperatureSetpoint))
        elif toggle == False:
            try: self.Camera.TemperatureSetpoint = self.config_dict.cooler_idle_setpoint
            except: pass
            else: print("Cooler Setpoint set to {0:.1f} C".format(self.Camera.TemperatureSetpoint))