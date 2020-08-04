# Condition Checker

import urllib.request
import urllib.error
import requests
import os
import re
import time
import threading
import logging
import datetime
import numpy as np

from PIL import Image

from ..common.util import time_utils, conversion_utils
from ..common.IO import config_reader


class Conditions(threading.Thread):
    
    def __init__(self):
        """
        Subclassed from threading.Thread.  Conditions periodically checks the humidity, wind, sun position, clouds, and
        rain while observing.

        Returns
        -------
        None.

        """
        super(Conditions, self).__init__(name='Conditions-Th')
        # Calls threading.Thread.__init__ with the name 'Conditions-Th'
        self.weather = None
        self.radar = None
        self.weather_alert = threading.Event() 
        self.stop = threading.Event()
        # Threading events to set flags and interact between threads
        self.config_dict = config_reader.get_config()                       # Global config dictionary
        self.weather_url = 'http://weather.cos.gmu.edu/Current_Monitor.htm'
        self.backup_weather_url = 'https://weather.com/weather/hourbyhour/' + \
                                  'l/e8321c2fb1f8234f40bf92ce494921d94e657d54cc2c01f1882755e04b761dee'
        # GMU COS Website for humitiy and wind
        self.rain_url = 'https://weather.com/weather/radar/interactive/' + \
                        'l/b63f24c17cc4e2d086c987ce32b2927ba388be79872113643d2ef82b2b13e813'
        # Weather.com radar for rain
        self.sun = False
        self.current_directory = os.path.abspath(os.path.dirname(__file__))
        
    def run(self):
        """
        Description
        -----------
        Calls self.weather_check and self.rain_check once every 15 minutes.  If conditions are clear, does nothing.
        If conditions are bad, stops observation_run and shuts down the observatory.

        Returns
        -------
        None.

        """
        last_rain = None
        if not self.check_internet():
            logging.error("Your internet connection requires attention.")
            return
        while not self.stop.isSet():
            (H, W, R) = self.weather_check()
            radar = self.rain_check()
            sun_elevation = conversion_utils.get_sun_elevation(datetime.datetime.now(datetime.timezone.utc),
                                                               self.config_dict.site_latitude,
                                                               self.config_dict.site_longitude)
            cloud_cover = self.cloud_check()
            if (H >= self.config_dict.humidity_limit) or (W >= self.config_dict.wind_limit) or \
                    (last_rain != R and last_rain is not None) or (radar is True) or (sun_elevation >= 0) or \
                    (cloud_cover is True):
                self.weather_alert.set()
                self.sun = True if sun_elevation >= 0 else False
                logging.critical("Weather conditions have become too poor for continued observing,"
                                 "or the Sun is rising.")
            else:
                logging.debug("Condition checker is alive: Last check false")
                last_rain = R
                self.weather_alert.clear()
            self.stop.wait(timeout=self.config_dict.weather_freq*60)

    @staticmethod
    def check_internet():
        """

        Returns
        -------
        BOOL
            True if Internet connection is verified, False otherwise.

        """
        try:
            urllib.request.urlopen('http://google.com')
            return True
        except (urllib.error.URLError, urllib.error.HTTPError):
            return False
   
    def weather_check(self):
        """

        Returns
        -------
        Humidity : FLOAT
            Current humidity (%) at Research Hall, from GMU COS weather station.
        Wind : FLOAT
            Current wind speeds in mph at Research Hall, from GMU COS weather station.
        Rain : FLOAT
            Current total rain in in. at Research Hall, from GMU COS weather station.

        """
        self.weather = urllib.request.urlopen(self.weather_url)
        header = requests.head(self.weather_url).headers
        backup = False
        if 'Last-Modified' in header:
            update_time = time_utils.convert_to_datetime_utc(header['Last-Modified'])
            diff = datetime.datetime.now(datetime.timezone.utc) - update_time
            if diff > datetime.timedelta(minutes=30):
                # Checking when the web page was last modified (may be outdated)
                logging.warning("GMU COS Weather Station Web site has not updated in the last 30 minutes! "
                                "Using backup weather.com to find humidity/wind/rain instead.")
                backup = True
        else: 
            logging.warning("GMU COS Weather Station Web site did not return a last modified timestamp"
                            "it may be outdated!")
            backup = True

        target_path = os.path.abspath(os.path.join(self.current_directory,
                                                   r'..\..\resources\weather_status\weather.txt'))
        if not backup:
            with open(target_path, 'w') as file:
                # Writes the html code to a text file
                for line in self.weather:
                    file.write(str(line)+'\n')

            with open(target_path, 'r') as file:
                # Reads the text file to find humidity, wind, rain
                text = file.read()
                conditions = re.findall(r'<font color="#3366FF">(.+?)</font>', text)
                humidity = float(conditions[1].replace('%', ''))
                if test_wind := re.search(r'[+-]?\d+\.\d+', conditions[3]):
                    wind = float(test_wind.group())
                else:
                    wind = None
                if test_rain := re.search(r'[+-]?\d+\.\d+', conditions[5]):
                    rain = float(test_rain.group())
                else:
                    rain = None
                return humidity, wind, rain
        else:
            s = requests.Session()
            weather_request = s.get(self.backup_weather_url, headers={'User-Agent': 'Mozilla/5.0'})

            with open(target_path, 'w') as file:
                # Writes the html code to a text file
                file.write(str(weather_request.content))

            with open(target_path, 'r') as file:
                # Reads the text file to find humidity, wind, rain
                text = file.read()
                humidity = re.search(r'<span data-testid="PercentageValue" class="_-_-components-src-molecule-' +
                                     r'DaypartDetails-DetailsTable-DetailsTable--value--2YD0-">(.+?)</span>',
                                     text).group(1)
                wind = re.search(r'<span data-testid="Wind" class="_-_-components-src-atom-WeatherData-Wind-Wind' +
                                 r'--windWrapper--3Ly7c undefined">(.+?)</span>', text).group(1)

                humidity = float(humidity.replace('%', ''))
                if test_wind := re.search(r'[+-]?\d+\.\d+', wind):
                    wind = float(test_wind.group())
                else:
                    wind = int(re.search(r'[+-]?\d', wind).group())
                rain = None
                return humidity, wind, rain

    def rain_check(self):
        """

        Returns
        -------
        BOOL
            True if there is rain nearby, False otherwise.

        """
        s = requests.Session()
        self.radar = s.get(self.rain_url, headers={'User-Agent': 'Mozilla/5.0'})
        target_path = os.path.abspath(os.path.join(self.current_directory, r'..\..\resources\weather_status\radar.txt'))
        with open(target_path, 'w') as file:
            # Writes weather.com html to a text file
            file.write(str(self.radar.text))
            
        epoch_sec = time_utils.datetime_to_epoch_milli_converter(datetime.datetime.utcnow()) / 1000
        esec_round = time_utils.rounddown_300(epoch_sec)
        # Website radar images only update every 300 seconds
        if abs(epoch_sec - esec_round) < 10:
            time.sleep(10 - abs(epoch_sec - esec_round))
        
        with open(target_path, 'r') as file:
            html = file.read()
            api_key = re.search(r'"SUN_V3_API_KEY":"(.+?)",', html).group(1)
            # Api key needed to access images, found from html
        
        coords = {0: '291:391:10', 1: '291:392:10', 2: '292:391:10', 3: '292:392:10'}
        # Radar map coordinates found by looking through html
        rain = []
        for key in coords:
            url = ('https://api.weather.com/v3/TileServer/tile?product=twcRadarMosaic'
                   + '&ts={}'.format(str(esec_round))
                   + '&xyz={}'.format(coords[key]) + '&apiKey={}'.format(api_key))
            # Constructs url of 4 nearest radar images
            path_to_images = os.path.abspath(os.path.join(
                self.current_directory, r'..\..\resources\weather_status\radar-img{0:04}.png'.format(key + 1)))
            
            with open(path_to_images, 'wb') as file:
                req = s.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                file.write(req.content)
                # Writes 4 images to local png files
            
            img = Image.open(path_to_images)
            px = img.size[0]*img.size[1]
            colors = img.getcolors()
            if len(colors) > 1:     # Checks for any colors (green to red for rain) in the images
                percent_colored = (1 - colors[-1][0] / px) * 100
                if percent_colored >= 10:
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
        
    def cloud_check(self):
        """
        Description
        -----------
        Checks the current cloud cover around Fairfax.

        Returns
        -------
        bool
            True if cloud cover reaches or exceeds the maximum percenage
            defined in the config file, otherwise False.

        """
        satellite = 'goes-16'
        day = int(time_utils.days_of_year())
        conus_band = 13
        _time = datetime.datetime.now(datetime.timezone.utc)
        year = _time.year
        time_round = time_utils.rounddown_300(_time.hour*60*60 + _time.minute*60 + _time.second)
        req = None
        s = requests.Session()
        for i in range(6):
            hour = int(time_round/(60*60))
            minute = int((time_round - hour*60*60)/60) - i
            _time = '{0:02d}{1:02d}'.format(hour, minute)
            if (minute - 1) % 5 != 0:
                continue
            url = 'https://www.ssec.wisc.edu/data/geo/images/goes-16/animation_images/' + \
                '{}_{}{}_{}_{}_conus.gif'.format(satellite, year, day, _time, conus_band)
            req = s.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        target_path = os.path.abspath(os.path.join(self.current_directory,
                                                   r'..\..\resources\weather_status\cloud-img.gif'))
        with open(target_path, 'wb') as file:
            file.write(req.content)
        
        if os.stat(target_path).st_size <= 2000:
            logging.error('Cloud coverage image cannot be retrieved')
            return False
        
        img = Image.open(target_path)
        img_array = np.array(img)
        img_array = img_array.astype('float64')
        # fairfax coordinates ~300, 1350
        img_internal = img_array[270:370, 1310:1410]
        img_small = Image.fromarray(img_internal)
        px = img_small.size[0]*img_small.size[1]
        colors = img_small.getcolors()
        clouds = [color for color in colors if color[1] > 30]
        percent_cover = sum([cloud[0] for cloud in clouds]) / px * 100
        img.close()
        img_small.close()
        if percent_cover >= self.config_dict.cloud_cover_limit:
            return True
        else:
            return False
