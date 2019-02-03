import subprocess,shlex
from array import *
import time
import win32com.client                 #Needed for telescope
from win32com.client import Dispatch   #Needed to Dispatch MaximDL and to use camera
import signal 
import _winreg
from datetime import datetime
import pywintypes
import math
import msvcrt
#import pythoncom     #needed if we use 'try' on Dispatch

telescope = win32com.client.Dispatch("ASCOM.Celestron.Telescope")
telescopeconnected=False
telescopecom=r'COM5'
cordwrapEnabled=False
#focuser = win32com.client.Dispatch("")
camera = win32com.client.Dispatch("MaxIm.CCDCamera")
cameraconnected = False

def checkTelescope():    # checking status of telescope
    global telescope
    global telescopeconnected
    writeregistrycommport(telescopecom) 
    if telescopeconnected== False:
            try:
                telescope.Connected=True
            except:
                print("unable to connect to telescope")
            if telescope.Connected:
                telescopeconnected=True
            else:
                telescopeconnected=False 
    return telescopeconnected

def disableCordwrap(): 
    global telescope
    global telescopeconnected
    global cordwrapEnabled
    if telescopeconnected==True:
        cordwrapcmd = "5001103900000002".decode("hex")
        output = telescope.CommandBlind(cordwrapcmd)
        cordwrapEnabled=True
    else:
        print("not connected")
        return cordwrapEnabled==False
        

def enableCordwrap():    #must run checkNexRemote first (as written)   
    global telescope
    global telescopeconnected
    global cordwrapEnabled
    if telescopeconnected==True:
        cordwrapcmd = "5001103800000002".decode("hex")
        output = telescope.CommandBlind(cordwrapcmd)
        cordwrapEnabled=True
    else:
        print("not connected")
        return cordwrapEnabled==False

     
def checkCordwrap():     ##determine if cordwrap is disabled, 00 disabled, FF enabled
    global telescope
    global telescopeconnected
    global cordwrapEnabled
    if telescopeconnected==True:
        cmd = "5001103B00000002".decode("hex")
        output = telescope.CommandString(cmd)
        time.sleep(3)
        if output == "00":
            return cordwrapEnabled==False
        else:
            return cordwrapEnabled==True
    else:
        return cordwrapEnabled==False
    
def setCordwrap():
    global telescope
    global telescopeconnected
    global cordwrapEnabled
    if telescopeconnected==True:
        cordwrapcmd = "5001103A00000002".decode("hex")
        output = telescope.CommandBlind(cordwrapcmd)
        cordwrapEnabled=True
    else:
        print("not connected")
        return cordwrapEnabled==False
        
def telescopemove(axis, direction, rate, duration):                    #replace rate and duration with distance (arcsec)
    '''
	axis=1 => altitude
	axis=0 => azimuth
	direction=1 => positive axis
	direction=0 => negative axis
	duration in seconds
	rate = telescope motor speed
	'''
    global telescope
    global telescopeconnected
    if telescopeconnected==True:
        if direction==1:
            dirtmp="24"
        else:
            dirtmp="25"
        if axis==1:
            axistmp="11"
        else:
            axistmp="10"
        movetmp = "5002"+axistmp+dirtmp+"0"+str(rate)+"000000"
        
        movecmd = movetmp.decode("hex")
        output = telescope.CommandBlind(movecmd)
        time.sleep(duration)
        stopmovetmp="5002"+axistmp+dirtmp+"00000000"
        stopmovecmd = stopmovetmp.decode("hex")
        output = telescope.CommandBlind(stopmovecmd)

    else:
        print("unable to communicate with telescope")

#Function to call ascom's slewtocordinates fuction. (move to specific RA and Dec)

