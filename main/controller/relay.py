import serial #Serial imported for Serial communication

ser = serial.Serial("COM8",9600) #Establish connection over COM8 and at a 9600 Baud rate

ser.open #Open the serial port for communication

while 1: #Establish a loop that continues forever

	var = input("Request: ") #Asks the user what they would like to do with the relay
	if var == "On": #Establishes that On means 1 (for the Arduino)
		var = "1"
	else: #Establishes that Off means 0 (for the Arduino)
		if var == "Off":
			var = "0"
		else: #Establishes that any other response is not a valid response
			var = "Not an accepted input"
			print(var)
			
	ser.write(var.encode()) #Sends the numbers, if eligible, to the Arduino
