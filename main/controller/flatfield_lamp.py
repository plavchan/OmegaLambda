# Flatfield Lamp Controller
import logging
import serial
import serial.tools.list_ports

from .hardware import Hardware

class FlatLamp(Hardware):
    
    def __init__(self):
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
        
        super(FlatLamp, self).__init__(name='FlatLamp')
        
    def TurnOn(self):
       try: self.ser.write('1'.encode()) 
       except: logging.error('Could not turn on the flatfield lamp')
       else: 
           print('The flat lamp is now on')
           self.status = 'on'
       
    def TurnOff(self):
       try: self.ser.write('0'.encode()) 
       except: logging.error('Could not turn off the flatfield lamp')
       else: 
           print('The flat lamp is now off')
           self.status = 'off'
       
    def disconnect(self):
        if self.status == 'on':
            self.TurnOff()
        try: self.ser.close()
        except: logging.error('Could not disconnect from the flatfield lamp')
        else: print('The flat lamp has disconnected')