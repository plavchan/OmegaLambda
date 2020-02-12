# -*- coding: utf-8 -*-
"""
Created on Wed Feb  5 18:55:17 2020

@author: purpl
"""

import time
import win32com.client

# NEEDS TESTING

class Telescope():
    def __init__(self):
        self.Telescope = win32com.client.Dispatch("ASCOM.Celestron.Telescope")
        self.connection = False
        self.Telescope.com = r'COM19' #Changed from COM5 to COM19 to match the current scope COM port on dev
        self.Telescope.cordwrapEnabled = False

    def checkTelescope(self):
        if self.Telescope.Connected == False: #not sure if this will work?
            try:
                self.Telescope.Connected = True
            except:
                print("unable to connect to telescope")
                if self.Telescope.Connected:
                    self.connection = True
        return self.connection
    
    def disableCordwrap(self):
        if self.Telescope.Connected == True:
            cordwrapcmd = "5001103900000002".decode("hex")
            output = self.Telescope.CommandBlind(cordwrapcmd)
            self.Telescope.cordwrapEnabled = True #Shouldn't this be false?
        else:
            print("not connected")
            return self.Telescope.cordwrapEnabled == False #Original telescope.py had a double equal? i.e. == False
        
    def enableCordwrap(self):
        if self.Telescope.Connected == True:
            cordwrapcmd = "5001103800000002".decode("hex")
            output = self.Telescope.CommandBlind(cordwrapcmd)
            self.Telescope.cordwrapEnabled = True
        else:
            print("not connected")
            return self.Telescope.cordwrapEnabled == False
    
    def checkCordwrap(self):
        if self.Telescope.Connected == True:
            cordwrapchk = "5001103B00000002".decode("hex")
            output = self.Telescope.CommandString(cordwrapchk)
            time.sleep(3)
            if output == "00":
                return self.Telescope.cordwrapEnabled == False
            else:
                return self.Telescope.cordwrapEnabled == True
        else:
            return self.Telescope.cordwrapEnabled == False
        
    def setCordwrap(self):
        if self.Telescope.Connected == True:
            cordwrapcmd = "5001103A00000002".decode("hex")
            output = self.Telescope.CommandBlind(cordwrapcmd)
            self.Telescope.cordwrapEnabled = True
        else:
            print("not connected")
            return self.Telescope.cordwrapEnabled == False
    
    def telescopemove(self, ra, dec):
        if self.Telescope.Connected == True:
            self.Telescope.Park()
            time.sleep(30)
            self.Telescope.Unpark()
            time.sleep(3)
            self.Telescope.SlewToCoordinates(ra, dec)
        
        
        
        
        
        
        
        
        
        
        
    
    
    