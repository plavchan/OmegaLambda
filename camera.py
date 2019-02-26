import subprocess,shlex
import time
import win32com.client                                              #I do not have this downloaded onto my system, so it appears as an error.
from win32com.client import Dispatch                                #Same as before 
import signal
import winreg                                                       #Same as before
import math
import pywintypes                                                   #Same as before
#import pythoncom                                                   #Needed if we use 'try' on Dispatch
GMUCamera=win32com.client.Dispatch("MaxIm.CCDCamera")               #Opens up MaxIm Dl as the GMUCamera
GMUCameraConnected=False                                            #For other Module uses in the future. Most likely Telescope and Commport module.
filepath = r'C:\Users\GMU Observtory1\Desktop\Test Pictures.fit'    #Sets the filepath for file saving. NEEDS THE '.fit' TO SAVE AN EXPOSURE FILE!!!
GMUCamera.DisableAutoShutdown=False                                 #Supposedly supposed to disable the disconnect on exit of application
GMUCamera.AutoDownload=True                                         #Allows the camera to auto download exposures.
def cameraSettings():                                               #Camera Settings definition
    GMUCamera.CoolerOn = True                                       #Turns on the cooler for the camera
    GMUCamera.Expose(1,1)                                           #Tells MaxIm Dl to take an exposure (Time, Light [,filter]) *filter is not necessarily needed*
    GMUCamera.StartDownload                                         #Tells MaxIm Dl to prepare the exposure for download
    print(GMUCamera.ImageReady)                                     #Prints the status of the image for when it is ready to download.
    while GMUCamera.ImageReady==False:                              #While loop for if and when the saving fails and produces a None
        time.sleep(20)                                              #EXTREMELY IMPORTANT!!! There is a gap in time where my code reads before the exposure is ready. This wait stops the problem
        print(GMUCamera.ImageReady)                                 #Prints the status of image for whether it is ready or not
        if GMUCamera.ImageReady==True:                              #Detects whether the exposure is ready to download
            GMUCamera.SaveImage(filepath)                           #Saves the exposure to the desktop
        else:
            None
try:
    GMUCamera.LinkEnabled = True                                    #Connects the code to MaxIm Dl
except:
    None
if GMUCamera.LinkEnabled == True:                                   #Gets function going
    GMUCamera.AutoDownload==True                                    #I put a second auto download here just to be sure. Works weirdly better here too
    print("Camera Connected")                                       #Prints message if camera is connected
    GMUCamera.DisableAutoShutdown == True                           #Still...in theory...supposed to stop disconnect when exiting the application
    GMUCameraConnected=True                                         #For future use in Telescope and possibly Commport modules
    print(cameraSettings())                                         #Runs the def
else:
    print("Camera is not connected")                                #Displays message if code is not connected 
    
    
#Save path module for the future