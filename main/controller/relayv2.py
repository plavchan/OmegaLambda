import serial #Serial imported for Serial communication
import time #Time imported for delays

status = "The flatfield lamp is currently off" #defining variable for the status command

ser = serial.Serial("COM4",9600) #Establish connection over COM4 and at a 9800 Baud rate

ser.open #Open the serial port for communication

while 1: #Establish a loop that continues forever

	var = input("Request: ") #Asks the user what they would like to do with the relay

#The following are the variables that are compared to the user's input:
	on = "on"
	off = "off"
	lampstatus = "status"
	shutdown = "shutdown"
	shutdownws = "shut down"
	
	if var.lower() == on: 
		var = "1" #Establishes that On means 1 (for the Arduino)
		status = "The flatfield lamp is currently on."
		print("The flatfield lamp is now on!")
	elif var.lower() == off: 
		var = "0" #Establishes that Off means 0 (for the Arduino)
		status = "The flatfield lamp is currently off."
		print("The flatfield lamp is now off!")
	elif var.lower() == shutdown or var.lower() == shutdownws:
		var = "0"
		ser.write(var.encode())
		print("The flatfield lamp is now off!")
		time.sleep(1)
		quit()
	elif var.lower() == lampstatus: 
		print(status)
	else: #Establishes that any other response is not a valid response
		var = "That was not an accepted input!"
		print(var)
	ser.write(var.encode()) #Sends the numbers, if eligible, to the Arduino
