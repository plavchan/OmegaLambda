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
        self.weather_url = 'http://weather.cos.gmu.edu/Current_Monitor.htm'
        self.rain_url = 'https://weather.com/weather/radar/interactive/l/b63f24c17cc4e2d086c987ce32b2927ba388be79872113643d2ef82b2b13e813'
        self.running = True
        
    def run(self):
        Last_Rain = None
        if not self.check_internet():
            print("ERROR: Your internet connection requires attention.")
            return
        while (self.weather_alert.isSet() == False) and (self.running == True):
            (H, W, R) = self.weather_check()
            Radar = self.rain_check()
            if (H >= self.config_dict.humidity_limit) or (W >= self.config_dict.wind_limit) or (Last_Rain != R and Last_Rain != None) or (Radar == True):
                self.weather_alert.set()
                print("Weather conditions have become too poor for continued observing.")
            else:
                logging.debug("Weather checker is alive: Last check false")
                Last_Rain = R
                time.sleep(self.config_dict.weather_freq*60)
                
    def stop(self):
        logging.debug("Stopping weather thread")
        self.running = False
                
    def check_internet(self):
        try:
            urllib.request.urlopen('http://google.com')
            return True
        except:
            return False
   
    def weather_check(self):
        self.weather = urllib.request.urlopen(self.weather_url)
        header = requests.head(self.weather_url).headers
        if 'Last-Modified' in header:
            Update_time = time_utils.convert_to_datetime_UTC(header['Last-Modified'])
            Diff = datetime.datetime.now(datetime.timezone.utc) - Update_time
            if Diff > datetime.timedelta(minutes=30):
                print("Warning: GMU COS Weather Station Web site has not updated in the last 30 minutes!")
                #Implement backup weather station
        else: 
            print("Warning: GMU COS Weather Station Web site did not return a last modified timestamp--it may be outdated!")
            #Implement backup weather station
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
        self.radar = s.get(self.rain_url, headers={'User-Agent': 'Mozilla/5.0'})
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