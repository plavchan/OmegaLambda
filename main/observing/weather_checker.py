#Weather Checker

import urllib.request
import re
import time
import threading
import logging
from main.common.IO import config_reader

# 85% Humidity
# 20 MPH winds
# 5% chance of precipitation

class Weather(threading.Thread):
    
    def __init__(self):
        super(Weather, self).__init__(name='Weather-Th')
        self.weather_alert = threading.Event()
        self.config_dict = config_reader.get_config()
        
    def run(self):
        Last_Rain = None
        while not self.weather_alert.isSet():
            (H, W, R) = self.weather_check()
            if (H >= self.config_dict.humidity_limit) or (W >= self.config_dict.wind_limit) or (Last_Rain != R and Last_Rain != None):
                self.weather_alert.set()
                print("Weather conditions have become too poor for continued observing.")
            else:
                logging.debug("Weather checker is alive: Last check false")
                Last_Rain = R
                time.sleep(15*60)    #Checks once every fifteen minutes
   
    def weather_check(self):
        self.weather = urllib.request.urlopen('http://weather.cos.gmu.edu/Current_Monitor.htm')
        with open(r'C:\Users\GMU Observtory1\-omegalambda\resources\weather.txt','w') as file:
            for line in self.weather:
                file.write(str(line)+'\n')
                
        with open(r'C:\Users\GMU Observtory1\-omegalambda\resources\weather.txt', 'r') as file:
            for line in file:
                if '<font color=Brown>Humidity</font>' in str(line):
                    file.readline()
                    Humidity = file.readline()
                    Humidity = int(re.search(r'\d+', Humidity.replace('b\' Helvetica"><strong><small><font color="#3366FF">', '')).group())
                elif '<font color=Brown><small>Wind<br></small></font>' in str(line):
                    file.readline()
                    Wind = file.readline()
                    Wind = float(re.search(r'\d+', Wind.replace('b\' Helvetica"><strong><font color="#3366FF">', '')).group())
                elif r'<font color=Brown>Today\'s Rain</font>' in str(line):
                    file.readline()
                    Rain = file.readline()
                    Rain = float(re.search("[+-]?\d+\.\d+", Rain.replace('b\' Helvetica"><strong><small><font color="#3366FF">', '')).group())
                else:
                    continue        
            return (Humidity, Wind, Rain)
        
    def rain_check(self):
        req = urllib.request.Request('https://weather.com/weather/radar/interactive/l/b63f24c17cc4e2d086c987ce32b2927ba388be79872113643d2ef82b2b13e813', 
                                     headers={'User-Agent': 'Mozilla/5.0'})
        self.radar = urllib.request.urlopen(req).read()
        with open(r'C:\Users\GMU Observtory1\-omegalambda\resources\radar.txt','w') as file:
            for line in self.radar:
                file.write(str(line) + '\n')
        
                