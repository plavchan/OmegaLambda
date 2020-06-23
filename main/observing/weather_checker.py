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

from ..common.util import time_utils
from ..common.IO import config_reader

class Weather(threading.Thread):
    
    def __init__(self):
        '''
        Description
        -----------
        Subclassed from threading.Thread.  Weather periodically checks the weather conditions while observing.

        Returns
        -------
        None.

        '''
        super(Weather, self).__init__(name='Weather-Th')                    # Calls threading.Thread.__init__ with the name 'Weather-Th'
        self.weather_alert = threading.Event()                              # Threading events to set flags and interact between threads
        self.config_dict = config_reader.get_config()                       # Global config dictionary
        self.weather_url = 'http://weather.cos.gmu.edu/Current_Monitor.htm'                                                                     #GMU COS Website for humitiy and wind
        self.rain_url = 'https://weather.com/weather/radar/interactive/l/b63f24c17cc4e2d086c987ce32b2927ba388be79872113643d2ef82b2b13e813'      #Weather.com radar for rain
        self.running = True
        
    def run(self):
        '''
        Description
        -----------
        Calls self.weather_check and self.rain_check once every 15 minutes.  If conditions are clear, does nothing.
        If conditions are bad, stops observation_run and shuts down the observatory.

        Returns
        -------
        None.

        '''
        Last_Rain = None
        if not self.check_internet():
            logging.error("Your internet connection requires attention.")
            return
        while (self.weather_alert.isSet() == False) and (self.running == True):
            (H, W, R) = self.weather_check()
            Radar = self.rain_check()
            if (H >= self.config_dict.humidity_limit) or (W >= self.config_dict.wind_limit) or (Last_Rain != R and Last_Rain != None) or (Radar == True):
                self.weather_alert.set()
                logging.critical("Weather conditions have become too poor for continued observing.")
            else:
                logging.debug("Weather checker is alive: Last check false")
                Last_Rain = R
                time.sleep(self.config_dict.weather_freq*60)
                
    def stop(self):
        '''
        Description
        -----------
        Sets self.running to False to stop run.

        Returns
        -------
        None.

        '''
        logging.debug("Stopping weather thread")
        self.running = False
                
    def check_internet(self):
        '''
        
        Returns
        -------
        BOOL
            True if Internet connection is verified, False otherwise.

        '''
        try:
            urllib.request.urlopen('http://google.com')
            return True
        except:
            return False
   
    def weather_check(self):
        '''

        Returns
        -------
        Humidity : FLOAT
            Current humitiy (%) at Research Hall, from GMU COS weather station.
        Wind : FLOAT
            Current wind speeds in mph at Research Hall, from GMU COS weather station.
        Rain : FLOAT
            Current total rain in in. at Research Hall, from GMU COS weather station.

        '''
        self.weather = urllib.request.urlopen(self.weather_url)
        header = requests.head(self.weather_url).headers
        if 'Last-Modified' in header:
            Update_time = time_utils.convert_to_datetime_UTC(header['Last-Modified'])
            Diff = datetime.datetime.now(datetime.timezone.utc) - Update_time
            if Diff > datetime.timedelta(minutes=30):                                                   # Checking when the web page was last modified (may be outdated)
                logging.warning("GMU COS Weather Station Web site has not updated in the last 30 minutes!")
                #Implement backup weather station
        else: 
            logging.warning("GMU COS Weather Station Web site did not return a last modified timestamp--it may be outdated!")
            #Implement backup weather station
        with open(os.path.join(self.config_dict.home_directory, r'resources\weather_status\weather.txt'),'w') as file:  # Writes the html code to a text file
            for line in self.weather:
                file.write(str(line)+'\n')
                
        with open(os.path.join(self.config_dict.home_directory, r'resources\weather_status\weather.txt'), 'r') as file:     # Reads the text file to find humidity, wind, rain
            text = file.read()
            conditions = re.findall(r'<font color="#3366FF">(.+?)</font>', text)
            Humidity = float(conditions[1].replace('%',''))
            Wind = float(re.search('[+-]?\d+\.\d+', conditions[3]).group())
            Rain = float(re.search('[+-]?\d+\.\d+', conditions[5]).group())
            
            return (Humidity, Wind, Rain)
        
    def rain_check(self):
        '''

        Returns
        -------
        BOOL
            True if there is rain nearby, False otherwise.

        '''
        s = requests.Session()
        self.radar = s.get(self.rain_url, headers={'User-Agent': 'Mozilla/5.0'})
        with open(os.path.join(self.config_dict.home_directory, r'resources\weather_status\radar.txt'),'w') as file:    # Writes weather.com html to a text file
            file.write(str(self.radar.text))
            
        epoch_sec = time_utils.datetime_to_epoch_milli_converter(datetime.datetime.utcnow()) / 1000
        esec_round = time_utils.rounddown_300(epoch_sec)
        # Website radar images only update every 300 seconds
        if abs(epoch_sec - esec_round) < 10:
            time.sleep(10 - abs(epoch_sec - esec_round))
        
        with open(os.path.join(self.config_dict.home_directory, r'resources\weather_status\radar.txt'), 'r') as file:
            html = file.read()
            apiKey = re.search(r'"SUN_V3_API_KEY":"(.+?)",', html).group(1)             # Api key needed to access images, found from html
        
        coords = {0: '291:391:10', 1: '291:392:10', 2: '292:391:10', 3: '292:392:10'}   # Radar map coordinates found by looking through html
        rain = []
        for key in coords:
            url = ( 'https://api.weather.com/v3/TileServer/tile?product=twcRadarMosaic' + '&ts={}'.format(str(esec_round)) 
                   + '&xyz={}'.format(coords[key]) + '&apiKey={}'.format(apiKey) )      # Constructs url of 4 nearest radar images
            
            with open(os.path.join(self.config_dict.home_directory, r'resources\weather_status\radar-img{0:04d}.png'.format(key + 1)), 'wb') as file:
                req = s.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                file.write(req.content)                                                 # Writes 4 images to local png files
            
            img = Image.open(os.path.join(self.config_dict.home_directory, r'resources\weather_status\radar-img{0:04d}.png'.format(key + 1)))
            px = img.size[0]*img.size[1]
            colors = img.getcolors()
            if len(colors) > 1:     # Checks for any colors (green to red for rain) in the images
                percent_colored = 1 - colors[-1][0] / px
                if percent_colored >= 0.1:
                    return True
                else:
                    rain.append(1)
            else:
                continue
            img.close()
        if sum(rain) >= 2:
            return True
        else:
            return False