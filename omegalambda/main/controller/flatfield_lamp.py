# Flatfield Lamp Controller
import logging
import serial
import serial.tools.list_ports
from serial.serialutil import SerialException
import threading
import time

from .hardware import Hardware

class FlatLamp(Hardware):
    startMarker = '<'
    endMarker = '>'
    idn_code = 2
    
    def __init__(self):
        """
        Initializes the flat lamp as a subclass of hardware.

        Returns
        -------
        None.

        """
        super(FlatLamp, self).__init__(name='FlatLamp')
        self.ser = serial.Serial()
        self.ser.baudrate = 9600
        self.status = None
        self.dataStarted = False
        self.dataBuf = ""
        self.flatfieldlamp_arduino = ""
        self.coolingsystem_arduino = ""
        self.messageComplete = False
        self.timeout = time.time() + 5
        self.lamp_done = threading.Event()
        
        ports = serial.tools.list_ports.comports()
        self.arduino_ports = []
        for p in ports:
            if p.manufacturer is not None and "Arduino" in p.manufacturer:
                self.arduino_ports.append(p.device)
        if len(self.arduino_ports) == 0:
            logging.critical('No Arduinos detected. Check and ensure they are plugged in!')
    
    
    '''
    Some of the functions are inspired by:
    https://forum.arduino.cc/t/pc-arduino-comms-using-python-updated/574496
    https://be189.github.io/lessons/10/control_of_arduino_with_python.html
    '''
    def receive_function(self):
        if self.ser.inWaiting() > 0 and not self.messageComplete:
            x = self.ser.read().decode()  # decode needed for Python3

            if self.dataStarted:
                if x != FlatLamp.endMarker:
                    self.dataBuf += x
                else:
                    self.dataStarted = False
                    self.messageComplete = True
            elif x == FlatLamp.startMarker:
                self.dataBuf = ''
                self.dataStarted = True

        if self.messageComplete:
            self.messageComplete = False
            return self.dataBuf
        else:
            return "XXX"
    
    def recv_arduino(self, **kwargs):
        port = kwargs.get('port', None)  # Check for overloaded variables
        
        recv = 'XXX'  # Reset recv
        while time.time() < self.timeout and (recv == 'XXX'):
            recv = self.receive_function()
        if not (recv == 'XXX'):
            return recv
        elif port is not None:
            logging.critical('Arduino @', port, 'timed out')
        else:
            logging.critical('An Arduino timed out')
    
    def arduino_identifier(self, port_arduino):
        try:
            self.ser.port = port_arduino
            self.ser.close()
            self.ser.open()
            _ = self.ser.read_all()

            check_ready = self.recv_arduino(port=port_arduino)

            if check_ready == 'Arduino is ready':
                self.ser.write(bytes([FlatLamp.idn_code]))
                id_reply = self.recv_arduino(port=port_arduino)

                if id_reply == 'LAMP':
                    self.flatfieldlamp_arduino = port_arduino
                if id_reply == 'COOLING':
                    self.coolingsystem_arduino = port_arduino
        finally:
            self.ser.close()  # Close serial port
    
    def get_port(self):
        for p in self.arduino_ports:
            self.arduino_identifier(p)
        
        if len(self.flatfieldlamp_arduino) == 0:
            logging.critical('Could not find flatfield lamp Arduino port')
        else:
            self.ser.port = self.flatfieldlamp_arduino

    def check_connection(self):
        """
        Description
        -----------
        Overwrites base class.  Checks for flatfield lamp connection specifically.

        Returns
        -------

        """
        logging.info("Checking connection for the {}".format(self.label))
        self.live_connection.clear()
        self.ser.open()
        self.live_connection.set()

    def _class_connect(self):
        """
        Description
        -----------
        Overrides base hardware class (not implemented).
        Should only ever be called from within the run method.

        Returns
        -------
        BOOL
            True if successful, otherwise False.
        """
        try:
            self.check_connection()
        except SerialException:
            logging.error('Could not connect to flatlamp')
            return False
        else:
            logging.info('Flatlamp has successfully connected')
        return True

    def turn_on(self):
        """
        Description
        -----------
        Turns on the flat lamp.

        Returns
        -------
        None.

        """
        self.lamp_done.clear()
        try:
            self.ser.write('1'.encode())
        except SerialException:
            logging.error('Could not turn on the flatfield lamp')
        else:
            logging.info('The flat lamp is now on')
            self.status = 'on'
            self.lamp_done.set()
       
    def turn_off(self):
        """
        Description
        -----------
        Turns off the flat lamp.

        Returns
        -------
        None.

        """
        self.lamp_done.clear()
        try:
            self.ser.write('0'.encode())
        except SerialException:
            logging.error('Could not turn off the flatfield lamp')
        else: 
            logging.info('The flat lamp is now off')
            self.status = 'off'
            self.lamp_done.set()
       
    def disconnect(self):
        """
        Description
        -----------
        Disconnects the flat lamp.

        Returns
        -------
        None.

        """
        if self.status == 'on':
            self.turn_off()
        try:
            self.ser.close()
        except SerialException:
            logging.error('Could not disconnect from the flatfield lamp')
        else:
            logging.info('The flat lamp has disconnected')