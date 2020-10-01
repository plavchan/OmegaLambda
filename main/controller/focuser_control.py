import logging
import threading
import time
import re
import serial
import serial.tools.list_ports
from serial.serialutil import SerialException

from .hardware import Hardware
from ..common.IO import config_reader


class Focuser(Hardware):
    
    def __init__(self):
        """
        Initializes the focuser as a subclass of hardware.

        Returns
        -------
        None.

        """
        super(Focuser, self).__init__(name='Focuser')      # calls Hardware.__init__ with the name 'focuser'
        self.ser = serial.Serial(timeout=0.5)
        self.ser.baudrate = 9600
        self.adjusting = threading.Event()
        self.adjustment_lock = threading.Lock()
        self.config_dict = config_reader.get_config()
        self.position = None
        self.temperature = None
        self.comport = ''

    def check_connection(self):
        """
        Description
        -----------
        Overwrites base class.  Checks for focuser connection specifically.

        Returns
        -------
        BOOL
            True if successful, otherwise False.
        """
        logging.info('Checking connection for the {}'.format(self.label))
        self.live_connection.clear()
        if self.ser.is_open:
            logging.info("Focuser has successfully connected")
            self.live_connection.set()
            return True
        else:
            logging.error("Could not connect to focuser")
            return False

    def _class_connect(self):
        """
        Description
        -----------
        Overrides base hardware class (not implemented).
        Dispatches pyserial connection to focuser object and sets necessary parameters.
        Should only ever be called from within the run method.

        Returns
        -------
        BOOL
            True if successful, otherwise False.
        """
        ports = list(serial.tools.list_ports.comports())
        com = [port for port in ports if "COM" in port.description]
        if len(com) >= 1:
            for comport in com:
                try:
                    self.ser.port = comport.device
                    self.ser.open()
                    self.ser.write("FV000000".encode())
                    if self.ser.readline() == b'FV003.20\xbf':
                        logging.info('The focuser connected to {}'.format(comport.description))
                        self.comport = comport.description
                        break
                    else:
                        self.ser.close()
                except SerialException:
                    logging.warning('Cannot connect to {}.  The port may already be in use. '
                                    'If the focuser connects, you may safely ignore this message.'.format(
                        comport.description))
        else:
            logging.error('No com ports found!')
        check = self.check_connection()
        return check

    def get_temperature(self):
        """
        Description
        -----------
        Provides the temperature detected by the RoboFocus sensors.

        Returns
        -------
        temp : FLOAT
            Temperature detected in degrees Celsius.
        """
        with self.adjustment_lock:
            self.adjusting.clear()
            try:
                self.ser.write("FT000000".encode())
                response = self.ser.readline()
                temp = (self._convert_response_to_int(response)/2 - 273)*(9/5) + 32
            except SerialException:
                logging.error('Could not read temperature')
            self.adjusting.set()
        self.temperature = temp
        return temp

    def current_position(self):
        """
        Description
        -----------
        Provides the current position of the RoboFocus mirror.

        Returns
        -------
        position : INT
            Current position in steps.
        """
        with self.adjustment_lock:
            self.adjusting.clear()
            try:
                self.ser.write("FI000000".encode())
                response = self.ser.readline()
                position = self._convert_response_to_int(response)
            except SerialException:
                logging.error('Could not read position')
            self.adjusting.set()
        self.position = position
        return position

    def move_in(self, amount: int):
        """
        Parameters
        ----------
        amount : INT
            The amount of steps to move the focuser in by.

        Returns
        -------
        BOOL
            True if successful, otherwise False.
        """
        with self.adjustment_lock:
            self.adjusting.clear()
            if amount < 0 or amount > self.config_dict.focus_max_distance:
                logging.error('Amount outside of safe movement range for focusing')
                return False
            zeros = "0" * (6 - len(str(amount)))
            command = "FI" + zeros + str(amount)
            try:
                self.ser.write(command.encode())
                logging.info('Moving in focuser by {} steps'.format(amount))
                position = self.ser.readline()
                self.position = self._convert_response_to_int(position)
                logging.info('The new focus position is {}'.format(self.position))
            except SerialException:
                logging.error('Could not move focuser in.')
            time.sleep(2)
            self.adjusting.set()
        return True

    def move_out(self, amount: int):
        """
         Parameters
         ----------
         amount : INT
             The amount of steps to move the focuser out by.

         Returns
         -------
         BOOL
             True if successful, otherwise False.
         """
        with self.adjustment_lock:
            self.adjusting.clear()
            if amount < 0 or amount > self.config_dict.focus_max_distance:
                logging.error('Amount outside of safe movement range for focusing')
                return False
            zeros = "0" * (6 - len(str(amount)))
            command = "FO" + zeros + str(amount)
            try:
                self.ser.write(command.encode())
                logging.info('Moving out focuser by {} steps'.format(amount))
                position = self.ser.readline()
                self.position = self._convert_response_to_int(position)
                logging.info('The new focus position is {}'.format(self.position))
            except SerialException:
                logging.error('Could not move focuser out.')
            time.sleep(2)
            self.adjusting.set()
        return True

    def absolute_move(self, abs_position: int):
        """
        Parameters
        ----------
        abs_position : INT
            Absolute position in steps to move the focuser to.

        Returns
        -------
        BOOL
            True if successful, otherwise False.
        """
        with self.adjustment_lock:
            self.adjusting.clear()
            if abs(abs_position - self.position) >= self.config_dict.focus_max_distance*2:
                logging.error('Absolute move amount outside of safe movement range for focusing')
                return False
            zeros = "0" * (6 - len(str(abs_position)))
            command = "FG" + zeros + str(abs_position)
            try:
                self.ser.write(command.encode())
                logging.info('Moving focuser to absolute position {}'.format(abs_position))
                while True:
                    response = self.ser.readline()
                    if b'FD' in response:
                        self.position = self._convert_response_to_int(response)
                        break
                logging.info('The new focus position is {}'.format(self.position))
            except SerialException:
                logging.error('Could not move to absolute position.')
            time.sleep(2)
            self.adjusting.set()
        return True

    def abort(self):
        """
        Description
        -----------
        Aborts the focuser command by sending an arbitrary command without waiting.  The command is just to respond
        with the firmware version number, but any commands sent during the processing of a previous command are
        interpreted as a stop command.

        Returns
        -------
        None
        """
        command = "FV000000"
        try:
            self.ser.write(command.encode())
            logging.info('Aborting focuser movement')
        except SerialException:
            logging.error('Unable to abort focuser move!')

    @staticmethod
    def _convert_response_to_int(response):
        """
        Description
        -----------
        Converts the read response from the focuser into an integer, if applicable.

        Parameters
        ----------
        response : BYTES
            The direct serial response from the focuser.

        Returns
        -------
        INT
            The value of the response as an integer.
        """
        temp_value = re.search('([0-9]+)', str(response))
        if temp_value:
            return int(temp_value.group())
        else:
            logging.error('Could not get integer from serial response')

    def disconnect(self):
        """
        Description
        -----------
        Disconnects from RoboFocus

        Returns
        -------
        None.

        """
        with self.adjustment_lock:
            try:
                self.ser.close()
                self.live_connection.clear()
            except SerialException:
                logging.error('Could not disconnect from the focuser!')
        
# Robofocus documentation: http://www.robofocus.com/documents/robofocusins31.pdf
