#Weather Checker

import urllib.request
import requests
import os
import re
import time
import threading
import logging
import datetime
from PIL import Image
from main.common.util import time_utils
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
            Radar = self.rain_check()
            if (H >= self.config_dict.humidity_limit) or (W >= self.config_dict.wind_limit) or (Last_Rain != R and Last_Rain != None) or (Radar == True):
                self.weather_alert.set()
                print("Weather conditions have become too poor for continued observing.")
            else:
                logging.debug("Weather checker is alive: Last check false")
                Last_Rain = R
                time.sleep(5*60)    #Checks once every five minutes
   
    def weather_check(self):
        self.weather = urllib.request.urlopen('http://weather.cos.gmu.edu/Current_Monitor.htm')
        with open(os.path.join(self.config_dict.home_directory, r'resources\weather_status\weather.txt'),'w') as file:
            for line in self.weather:
                file.write(str(line)+'\n')
                
        with open(os.path.join(self.config_dict.home_directory, r'resources\weather_status\weather.txt'), 'r') as file:
            text = file.read()
            conditions = re.findall(r'<font color="#3366FF">(.+?)</font>', text)
            Humidity = float(conditions[1].replace('%',''))
            Wind = float(re.search('[+-]?\d+\.\d+', conditions[3]).group())
            Rain = float(re.search('[+-]?\d+\.\d+', conditions[5]).group())
            
            return (Humidity, Wind, Rain)
        
    def rain_check(self):
        s = requests.Session()
        self.radar = s.get('https://weather.com/weather/radar/interactive/l/b63f24c17cc4e2d086c987ce32b2927ba388be79872113643d2ef82b2b13e813', 
                                     headers={'User-Agent': 'Mozilla/5.0'})
        with open(os.path.join(self.config_dict.home_directory, r'resources\weather_status\radar.txt'),'w') as file:
            file.write(str(self.radar.text))
            
        epoch_sec = time_utils.datetime_to_epoch_milli_converter(datetime.datetime.utcnow()) / 1000
        esec_round = time_utils.rounddown_300(epoch_sec)
        #Want to round to lower 300 since site only updates every 300 secs (on 300s)
        if abs(epoch_sec - esec_round) < 10:
            time.sleep(10 - abs(epoch_sec - esec_round))
        
        with open(os.path.join(self.config_dict.home_directory, r'resources\weather_status\radar.txt'), 'r') as file:
            html = file.read()
            apiKey = re.search(r'"SUN_V3_API_KEY":"(.+?)",', html).group(1)             #Api key needed to access images, found from html
        
        coords = {0: '291:391:10', 1: '291:392:10', 2: '292:391:10', 3: '292:392:10'}   #Radar map coordinates found by looking through html
        rain = []
        for key in coords:
            url = ( 'https://api.weather.com/v3/TileServer/tile?product=twcRadarMosaic' + '&ts={}'.format(str(esec_round)) 
                   + '&xyz={}'.format(coords[key]) + '&apiKey={}'.format(apiKey) )
            
            with open(os.path.join(self.config_dict.home_directory, r'resources\weather_status\radar-img{0:04d}.png'.format(key + 1)), 'wb') as file:
                req = s.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                file.write(req.content)
            
            img = Image.open(os.path.join(self.config_dict.home_directory, r'resources\weather_status\radar-img{0:04d}.png'.format(key + 1)))
            colors = img.getcolors()
            if colors[0][0] > 1 or len(colors) > 1:     #Checks for any colors (green to red for rain) in the images
                return True
            else:
                continue
            img.close()
        return False