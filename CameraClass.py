import subprocess,shlex
import time
import win32com.client                 
from win32com.client import Dispatch     
import signal
import winreg                          
import math
import pywintypes

class Camera:
    def __init__(self):                                         #Learned a Little about __init__(self)
        Camera=win32com.client.Dispatch("MaxIm.CCDCamera")      #Sets the camera connection path to the CCDCamera
        Camera.DisableAutoShutdown == True                      #All of these settings are just basic camera setup settings.
        Camera.LockApp == True   
        Camera.CoolerOn == True     
        Camera.AutoDownload==True                   
        try:
            Camera.LinkEnabled == True
            if Camera.LinkEnabled==True:
                print("Camera is connected")
        except:
            print("Camera is not Connected")
            None
    def Exposures(self,length,Filter):
        Camera=win32com.client.Dispatch("MaxIm.CCDCamera")
        print("Lets collect them photons!")
        length=input("How long do you want your exposure?")     #length and x are meant to be temporary user input for testing purposes. 
        x=input("Type 1 for light frame, 0 for dark frame")
        if x==1:                        #This entire if statement is to allow the choice between light and dark frames. Could be reworked for full automation, but a good temporary placement.
            return x
        elif x==0:
            return x
        else:
            print("Not acceptable")
            None
        Camera.SetFullFrame()                           #Sets the full frame of the exposure. Could react wrong with binning process. 
        Camera.Expose(length,x,Filter)
        while Camera.ImageReady==False:
            time.sleep(20)                          #Move this around to find max efficiency 
            print(Camera.ImageReady)
            if Camera.ImageReady==True:                     #If the Image is ready for download, the download process starts and saves the exposure onto the desktop.
                Camera.StartDownload                            
                Camera.SaveImage(r'C:\Users\GMU Observtory1\Desktop\Test Pictures.fit')     #Filepath was copy and pasted from old code
            else:
                None

    def Binning(self):
        Camera=win32com.client.Dispatch("MaxIm.CCDCamera")
        Camera.BinningXY==False                                #Made for simplicities sake, cvan be reworked for a less rigid binning later. Change to True for more customizability
        a=input("What binning factor would you like? *This factor is equal for both X and Y axis")
        Camera.BinX=a

    def Filters(self):
        Camera=win32com.client.Dispatch("MaxIm.CCDCamera")
        print(Camera.FilterWheelName)       #These are meant to give information about the filters already in place 
        print(Camera.FilterNames)
        print(Camera.HasFilterWheel)
    
    def Gain(self):
        Camera=win32com.client.Dispatch("MaxIm.CCDCamera")
        ElectronsPerADU=input("Input Gain Factor wanted")
        Background=0
        BlackLevelOffset=0
        Uniform=0
        Camera.SetNoise([ElectronsPerADU [, Background [, BlackLevelOffset [, Uniform]]]])
    print(__init__)
    time.sleep(3)
    print(Binning)
    time.sleep(3)
    print(Filters)
    time.sleep(3)
    print(Gain)
    time.sleep(3)
    print(Exposures)


