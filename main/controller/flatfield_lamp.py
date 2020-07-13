# Flatfield Lamp Controller
import logging
import serial
import serial.tools.list_ports
import threading

from .hardware import Hardware

class FlatLamp(Hardware):
    
    def __init__(self):
        '''
        Initializes the flat lamp as a subclass of hardware.

        Returns
        -------
        None.

        '''
        self.ser = serial.Serial()
        self.ser.baudrate = 9600
        self.status = None
        ports = list(serial.tools.list_ports.comports())
        Arduino_ports = []
        for port in ports:
            if "Arduino" in port.description:
                Arduino_ports.append(port)
        
        if len(Arduino_ports) >= 1:
            self.ser.port = Arduino_ports[0].device
        else:
            logging.critical('Cannot find flatfield lamp port')
            return
        
        self.lamp_done = threading.Event()
        super(FlatLamp, self).__init__(name='FlatLamp')
        
    def TurnOn(self):
        '''
        Description
        -----------
        Turns on the flat lamp.

        Returns
        -------
        None.

        '''
        self.lamp_done.clear()
        try: self.ser.write('1'.encode()) 
        except: logging.error('Could not turn on the flatfield lamp')
        else: 
            print('The flat lamp is now on')
            self.status = 'on'
            self.lamp_done.set()
       
    def TurnOff(self):
        '''
        Description
        -----------
        Turns off the flat lamp.

        Returns
        -------
        None.

        '''
        self.lamp_done.clear()
        try: self.ser.write('0'.encode()) 
        except: logging.error('Could not turn off the flatfield lamp')
        else: 
            print('The flat lamp is now off')
            self.status = 'off'
            self.lamp_done.set()
       
    def disconnect(self):
        '''
        Description
        -----------
        Disconnects the flat lamp.

        Returns
        -------
        None.

        '''
        if self.status == 'on':
            self.TurnOff()
        try: self.ser.close()
        except: logging.error('Could not disconnect from the flatfield lamp')
        else: print('The flat lamp has disconnected')