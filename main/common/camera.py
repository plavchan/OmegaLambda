import os
import subprocess, shlex
import time
import win32com.client
from win32com.client import Dispatch
import signal
import winreg
import math
import pywintypes                                                                   #Not all are necessarily important


class Camera():                                                                     
    def __init__(self,camera):                                                      #initial function. just needs to take up space to function correctly.
        self.camera=camera

    def expose(self,exposure_time,type,filter):                                     #Exposure function that does all the main work.
        camera=win32com.client.Dispatch("MaxIm.CCDCamera")                          #Opens MaxIm Dl
        try:                                                                        #Try statement does the connection. ONLY ONE "="!!!!
            camera.LinkEnabled=True
            print("Camera is connected")
        except:
            print("Camera is not connected")
            return
        camera.DisableAutoShutdown                                                  #Not sure if really works
        if camera.LinkEnabled==True:                                                #Does work if camera is connected
            camera.Expose(exposure_time,type,filter)                                #starts exposure using variables set in the driver
            camera.StartDownload                                                    #starts download of the exposure
            print(camera.ImageReady)                                                #tester
            while camera.ImageReady==False:                                         #If the exposure is not ready for saving, it waits 20 seconds for exposure to load
                time.sleep(20)                                                      #VERY IMPORTANT
                print(camera.ImageReady)                                            #tester
                if camera.ImageReady==True:                                         #Saves image if there is an image to save.
                    print(camera.ImageReady)                                        #tester
                    path = os.path.expanduser('~/Desktop')                          
                    camera.SaveImage(os.path.join(path, "test_pictures.fit"))       #Saves image to Desktop
 
    def set_gain(self):
        pass

    def set_binning(self):
        pass