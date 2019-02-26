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

GMUTelescope = win32com.client.Dispatch("ASCOM.Celestron.Telescope")
GMUTelescopeConnected=False
GMUTelescopeCom=r'COM5'
cordwrapEnabled=False
#focuser = win32com.client.Dispatch("")
camera = win32com.client.Dispatch("MaxIm.CCDCamera")
cameraconnected = False

def writeregistrycommport(commport):
    reg = _winreg.ConnectRegistry(None,_winreg.HKEY_LOCAL_MACHINE)
    comkey = _winreg.OpenKey(reg, r"SOFTWARE\Wow6432Node\ASCOM\Telescope Drivers\ASCOM.Celestron.Telescope",0,_winreg.KEY_WRITE)
    _winreg.SetValueEx(comkey, 'CommPort',0, _winreg.REG_SZ, telescopecom)
    _winreg.FlushKey(comkey)
    _winreg.CloseKey(comkey) 	

def getregistrycommportvalue():
    reg = _winreg.ConnectRegistry(None,_winreg.HKEY_LOCAL_MACHINE)
    comkey = _winreg.OpenKey(reg, r"SOFTWARE\Wow6432Node\ASCOM\Telescope Drivers\ASCOM.Celestron.Telescope",0,_winreg.KEY_ALL_ACCESS)
    tmp = _winreg.QueryValueEx(comkey,'CommPort')
    print tmp[0]
    _winreg.FlushKey(comkey)
    _winreg.CloseKey(comkey) 