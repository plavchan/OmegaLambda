# Condition Checker

import urllib.request
import urllib.error
import urllib3.exceptions
import requests
import requests.exceptions
import os
import re
import threading
import logging
import datetime
import json
import time
import numpy as np
import matplotlib

from PIL import Image

from ..common.util import time_utils, conversion_utils
from ..common.IO import config_reader

# Use the non-interactive Agg backend, which does not have the memory leak problems associated with the deafult
# TkAgg backend upon closing plots.  This is necessary for long runs where we expect to generate hundreds if not
# thousands of diagnostic plots in the background.
matplotlib.use('Agg', force=True)
from matplotlib import pyplot as plt
from matplotlib import colors as mplc


class Conditions(threading.Thread):

    def __init__(self, plot_lock=None):
        """
        Subclassed from threading.Thread.  Conditions periodically checks the humidity, wind, sun position, clouds, and
        rain while observing.

        Parameters
        ----------
        plot_lock : threading.Lock
            A thread lock to prevent multiple matplotlib plots from being opened simultaneously across different threads.

        Returns
        -------
        None.

        """
        super(Conditions, self).__init__(name='Conditions-Th', daemon=True)
        # Calls threading.Thread.__init__ with the name 'Conditions-Th'
        self.weather = None
        self.radar = None
        self.weather_alert = threading.Event()
        self.connection_alert = threading.Event()
        self.stop = threading.Event()
        self.plot_lock = plot_lock
        # Threading events to set flags and interact between threads
        self.config_dict = config_reader.get_config()  # Global config dictionary
        # GMU COS Website for temperature, humidity and wind
        self.weather_url = 'http://weather.cos.gmu.edu/Current_Monitor.htm'
        # weather.gov API for backup temperature, humidity and wind
        # self.backup_weather_url = "https://api.weather.gov/points/38.8286,-77.3062"
        self.backup_weather_url = "https://api.weatherapi.com/v1/current.json?key=fe686757107d46519c010740232712&q=22030"
        # Weather.com radar for rain
        self.rain_url = 'https://weather.com/weather/radar/interactive/' + \
                        'l/b63f24c17cc4e2d086c987ce32b2927ba388be79872113643d2ef82b2b13e813'
        self.sun = False
        self.temperature = None
        current_directory = os.path.abspath(os.path.dirname(__file__))
        self.weather_directory = os.path.join(current_directory, r'..', r'..', r'resources', r'weather_status')

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
        connection_failures = 0
        if not self.check_internet():
            logging.error("Your internet connection requires attention.")
            return
        while not self.stop.isSet():
            (humidity, wind, rain, temperature) = self.weather_check()
            self.temperature = temperature
            radar = self.rain_check()
            sun_elevation = conversion_utils.get_sun_elevation(datetime.datetime.now(datetime.timezone.utc),
                                                               self.config_dict.site_latitude,
                                                               self.config_dict.site_longitude)
            cloud_cover = self.cloud_check()
            if self.connection_alert.isSet():
                connection_failures += 1
                if connection_failures >= 2:
                    self.weather_alert.set()
                    logging.critical("A connection error was encountered and the weather can no longer be monitored. "
                                     "Shutting down for safety.")
                    connection_failures = 0
                    self.stop.wait(timeout=self.config_dict.weather_freq * 60)
                    self.connection_alert.clear()
                    continue
            if humidity is None or wind is None:
                logging.warning('Could not retrieve humidity or wind values...it may be unsafe to continue observing.')
            if (humidity is None or humidity >= self.config_dict.humidity_limit) or \
                    (wind is None or wind >= self.config_dict.wind_limit) or \
                    (rain not in (None, 0) and last_rain is not None and last_rain != rain) or \
                    (radar is True) or (sun_elevation >= (-5)) or (cloud_cover is True):
                self.weather_alert.set()
                # -12 degrees: nautical twilight, adjust slightly to allow observations to start earlier
                self.sun = (sun_elevation >= (-5))
                message = ""
                message += "| Humidity |" if (humidity is None or humidity >= self.config_dict.humidity_limit) else ""
                message += "| Wind |" if (wind is None or wind >= self.config_dict.wind_limit) else ""
                message += "| Rain |" if (rain not in (None, 0) and last_rain is not None and last_rain != rain) else ""
                message += "| Nearby Rain |" if radar else ""
                message += "| Sun Elevation |" if self.sun else ""
                message += "| Clouds |" if cloud_cover else ""
                logging.critical("Weather conditions have become too poor for continued observing. "
                                 "Reason(s) for weather alert: {}".format(message))
            else:
                logging.debug("Condition checker is alive: Last check false")
                self.weather_alert.clear()
            last_rain = rain
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
        Temperature : FLOAT
            Current temperature in degrees F at Research Hall, from GMU COS weather station.

        For temperature, humidity and wind weather.gov is used as a backup.
        For rain, weather.com radar is used as a backup.

        """
        s = requests.Session()
        humidity = wind = rain = temperature = None
            
        ## GMU COS Weather Station Website is no longer functional. 
        ## Commenting out this section until new website comes online.
        # try:
        #     header = requests.head(self.weather_url).headers
        # except (urllib3.exceptions.MaxRetryError, urllib3.exceptions.HTTPError, urllib3.exceptions.TimeoutError,
        #         urllib3.exceptions.InvalidHeader, requests.exceptions.ConnectionError, requests.exceptions.Timeout,
        #         requests.exceptions.HTTPError):
        #     logging.warning('Failed to read GMU website header')
        #     backup = True
        # else:
        #     if 'Last-Modified' in header:
        #         if True:
        #             # Checking when the web page was last modified (may be outdated)
        #             logging.warning("GMU COS Weather Station Web site has not updated in the last 30 minutes! "
        #                             "Using backup weather.com to find humidity/wind/rain instead.")
        #             backup = True
        #     else:
        #         logging.warning("GMU COS Weather Station Web site did not return a last modified timestamp, "
        #                         "it may be outdated!")
        #         backup = True
            
        backup = True
        target_path = os.path.abspath(os.path.join(self.weather_directory, r'weather.txt'))
        if not backup:
            try:
                self.weather = s.get(self.weather_url)
            except (urllib3.exceptions.MaxRetryError, urllib3.exceptions.HTTPError, urllib3.exceptions.TimeoutError,
                    urllib3.exceptions.InvalidHeader, requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                    requests.exceptions.HTTPError):
                self.connection_alert.set()
                return None, None, None, None
            conditions = re.findall(r'<font color="#3366FF">(.+?)</font>', self.weather.text)
            if '-' not in conditions[1]:
                humidity = float(conditions[1].replace('%', ''))
            if temperature_0 := re.search(r'[+-]?\d+\.\d+', conditions[0]):
                temperature = float(temperature_0.group())
            if test_wind := re.search(r'[+-]?\d+\.\d+', conditions[3]):
                wind = float(test_wind.group())
            if test_rain := re.search(r'[+-]?\d+\.\d+', conditions[5]):
                rain = float(test_rain.group())

        if backup or (None in (humidity, wind, rain)):
            success = False
            encountered_error = False
            
            for i in range(1, 9):
                if i != 1:
                    time.sleep(6 * i)

                try:
                    self.weather = s.get(self.backup_weather_url, headers={'User-Agent': self.config_dict.user_agent})
                    
                except (urllib3.exceptions.MaxRetryError, urllib3.exceptions.HTTPError, urllib3.exceptions.TimeoutError,
                        urllib3.exceptions.InvalidHeader, requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                        requests.exceptions.HTTPError, json.decoder.JSONDecodeError, KeyError) as e:
                    logging.warning(f"Could not connect to weatherapi.com API: try {i}")
                    logging.exception(e)
                    encountered_error = True
                    continue
                
                try:
                    res = json.loads(self.weather.text)
                    temperature = float(res['current']['temp_f'])
                    humidity = float(res['current']['humidity'])
                    wind = float(res['current']['wind_mph'])
                    
                    success = True
                    break
                    
                except (json.decoder.JSONDecodeError, KeyError) as e:
                    logging.warning(f"Failed to read weatherapi.com API: try {i}")
                    # logging.exception(e)
                    logging.info(self.weather.text)
                    encountered_error = True
                                
            if not success:
                logging.warning(f"Could not read weatherapi.com  after {i} tries. Setting connection alert.")
                self.connection_alert.set()
                return None, None, None, None
            
            if success and encountered_error:
                logging.info(f"Successfully read weatherapi.com after {i} tries.")
                
        # weather.gov
        # if backup or (None in (humidity, wind, rain)):
        #     success = False
        #     encountered_error = False
            
        #     for i in range(1, 9):
        #         if i != 1:
        #             time.sleep(6 * i)

        #         try:
        #             # weather.gov API process:
        #             # 1. Get metadata for location from latitude and longitude
        #             # 2. Lookup hourly forecast for location from metadata
        #             # The zone for step 2 might occasionally change, which is why the 2-step process is needed.
                    
        #             weather_metadata = s.get(self.backup_weather_url, headers={'User-Agent': self.config_dict.user_agent})
        #             res = json.loads(weather_metadata.text)
        #             self.weather = s.get(res["properties"]["forecastHourly"], headers={'User-Agent': self.config_dict.user_agent})
                    
        #         except (urllib3.exceptions.MaxRetryError, urllib3.exceptions.HTTPError, urllib3.exceptions.TimeoutError,
        #                 urllib3.exceptions.InvalidHeader, requests.exceptions.ConnectionError, requests.exceptions.Timeout,
        #                 requests.exceptions.HTTPError, json.decoder.JSONDecodeError, KeyError) as e:
        #             logging.warning(f"Could not connect to weather.gov API: try {i}")
        #             # logging.exception(e)
        #             encountered_error = True
        #             continue
                
        #         try:
        #             res = json.loads(self.weather.text)
        #             temperature = float(res['properties']['periods'][0]['temperature'])
        #             humidity = float(res['properties']['periods'][0]['relativeHumidity']["value"])
        #             wind = res['properties']['periods'][0]['windSpeed']
                    
        #             # Wind returns two formats: (1) # mph and (2) # to # mph. Remove "mph" for (1). Remove "mph" and take the max for (2).
        #             wind = wind.split()
        #             max_wind = -1
        #             for word in wind:
        #                 if word in ("mph", "to"):
        #                     continue
        #                 try:
        #                     word = float(word)
        #                     max_wind = max(max_wind, word)
        #                 except ValueError as e:
        #                     logging.warning(f"Failed to read weather.gov wind API: try {i}")
        #                     # logging.exception(e)
                            
        #             wind = max_wind
        #             if wind == -1:
        #                 logging.warning(f"Failed to read weather.gov wind API - max_wind not found: try {i}")
        #                 wind = None
        #                 encountered_error = True
        #                 continue
                    
        #             success = True
        #             break
                    
        #         except (json.decoder.JSONDecodeError, KeyError) as e:
        #             logging.warning(f"Failed to read weather.gov API: try {i}")
        #             # logging.exception(e)
        #             logging.info(self.weather.text)
        #             encountered_error = True
                                
        #     if not success:
        #         logging.warning(f"Could not read weather.gov API after {i} tries. Setting connection alert.")
        #         self.connection_alert.set()
        #         return None, None, None, None
            
        #     if success and encountered_error:
        #         logging.info(f"Successfully read weather.gov API after {i} tries.")

        with open(target_path, 'w') as file:
            # Writes the html code to a text file
            file.write(str(self.weather.content))

        logging.debug(f"Humidity: {humidity}, Wind: {wind}, Temperature: {temperature}")
        return humidity, wind, rain, temperature

    def rain_check(self):
        """

        Returns
        -------
        BOOL
            True if there is rain nearby, False otherwise.

        """
        s = requests.Session()
        try:
            self.radar = s.get(self.rain_url, headers={'User-Agent': self.config_dict.user_agent})
        except (urllib3.exceptions.MaxRetryError, urllib3.exceptions.HTTPError, urllib3.exceptions.TimeoutError,
                urllib3.exceptions.InvalidHeader, requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                requests.exceptions.HTTPError):
            self.connection_alert.set()
            return None
        # api_key = re.search(r'"SUN_V3_API_KEY":"(.+?)",', self.radar.text).group(1)
        # API key needed to access radar images from the weather.com website
        api_key = re.search(r'{}'.format(self.config_dict.weather_api_key), self.radar.text)
        if api_key:
            api_key = api_key.group(2)
            logging.debug('API Key for weather.com was successful!')
        else:
            logging.warning('Could not retrieve weather.com API key.  Continuing without radar checks.')
            self.connection_alert.set()
            return None

        target_path = os.path.abspath(os.path.join(self.weather_directory, r'radar.txt'))
        try:
            with open(target_path, 'w') as file:
                # Writes weather.com html to a text file
                file.write(str(self.radar.content))
        except (UnicodeError, UnicodeEncodeError, UnicodeDecodeError):
            logging.warning('Could not save weather.com html due to a unicode error.')

        epoch_sec = time_utils.datetime_to_epoch_milli_converter(datetime.datetime.utcnow()) / 1000
        esec_round = int(time_utils.rounddown_300(epoch_sec) - 300)
        # Website radar images only update every 300 seconds

        coords = {0: '291:391:10', 1: '291:392:10', 2: '292:391:10', 3: '292:392:10'}
        # Radar map coordinates found by looking through html
        rain = []
        for key in coords:
            url = ('https://api.weather.com/v3/TileServer/tile?product=twcRadarMosaic'
                   + '&ts={}'.format(str(esec_round))
                   + '&xyz={}'.format(coords[key]) + '&apiKey={}'.format(api_key))
            # Constructs url of 4 nearest radar images
            path_to_images: str = os.path.abspath(os.path.join(
                self.weather_directory, r'radar-img{0:04}.png'.format(key + 1)))
            try:
                req = s.get(url, headers={'User-Agent': self.config_dict.user_agent})
            except (urllib3.exceptions.MaxRetryError, urllib3.exceptions.HTTPError, urllib3.exceptions.TimeoutError,
                    urllib3.exceptions.InvalidHeader, requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                    requests.exceptions.HTTPError):
                self.connection_alert.set()
                return None
            with open(path_to_images, 'wb') as file:
                file.write(req.content)
                # Writes 4 images to local png files
            logging.debug('Weather.com radar image url: {}'.format(url))
            img = Image.open(path_to_images).convert("RGBA")
            px = img.size[0] * img.size[1]
            colors = np.array(img.getcolors())
            if len(colors) > 1:  # Checks for any colors (green to red for rain) in the images
                colsum = [np.nansum(colors[:, 1][i]) for i in range(len(colors))]
                uncolored_i = np.where(np.isclose(colsum, 0))[0]
                if uncolored_i.size > 0:
                    percent_colored = (1 - colors[uncolored_i][0][0] / px) * 100
                    logging.debug('Rain percentage: {:.5f}'.format(percent_colored))
                    img.close()
                    if percent_colored >= self.config_dict.rain_percent_limit:
                        return True
                    else:
                        rain.append(1)
                else:
                    return True
            else:
                img.close()
                continue
        if sum(rain) >= 4:
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

        TODO: Use weather.com or another source to get cloud cover and take the max of that and satellite data?
        """
        satellite = self.config_dict.cloud_satellite
        day = int(time_utils.days_of_year())
        conus_band = 13
        _time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
        year = _time.year
        time_round = time_utils.rounddown_300(_time.hour * 60 * 60 + _time.minute * 60 + _time.second)
        req = None
        s = requests.Session()
        for i in range(6):
            hour = int(time_round / (60 * 60))
            minute = int((time_round - hour * 60 * 60) / 60) - i
            if minute < 0:
                hour -= 1
                minute += 60
            if hour < 0:
                day -= 1
                hour += 24
            if day < 0:
                year -= 1
                day += 365
            _time = '{0:02d}{1:02d}'.format(hour, minute)
            if (minute - 1) % 5 != 0:
                continue
            daystr = str(day).zfill(3)
            url = 'https://www.ssec.wisc.edu/data/geo/images/goes-16/animation_images/' + \
                '{}_{}{}_{}_{}_conus.gif'.format(satellite, year, daystr, _time, conus_band)
            try:
                req = s.get(url, headers={'User-Agent': self.config_dict.user_agent})
                break
            except (urllib3.exceptions.MaxRetryError, urllib3.exceptions.HTTPError, urllib3.exceptions.TimeoutError,
                    urllib3.exceptions.InvalidHeader, requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                    requests.exceptions.HTTPError):
                self.connection_alert.set()
                return None
        target_path = os.path.abspath(os.path.join(self.weather_directory, r'cloud-img.gif'))
        with open(target_path, 'wb') as file:
            file.write(req.content)

        if os.stat(target_path).st_size <= 2000:
            logging.error('Cloud coverage image cannot be retrieved')
            return False

        img = Image.open(target_path)
        img_array = np.array(img)
        img_array = img_array.astype('float64')
        # fairfax coordinates ~300, 1350
        img_internal = img_array[295:335, 1340:1380]
        img_small = Image.fromarray(img_internal)
        px = img_small.size[0] * img_small.size[1]
        colors = img_small.getcolors()
        percent_cover = sum([(0, colorn)[colorp - self.config_dict.cloud_saturation_limit >= 0] for (colorn, colorp) in colors]) / px * 100
        logging.debug('Cloud coverage (%): {:.5f}'.format(percent_cover))
        if not isinstance(self.plot_lock, type(None)):
            self.plot_lock.acquire()
        else:
            logging.warning('No thread lock is being utilized for plot drawing: plots may draw incorrectly!')
        colornorm = mplc.Normalize(vmin=0, vmax=256)
        fig, ax = plt.subplots()
        plot = ax.imshow(img_internal, cmap=plt.get_cmap('PuOr'), norm=colornorm)
        pos = ax.get_position()
        cbar_ax = fig.add_axes([0.83, pos.y0, 0.025, pos.height])
        cbar = fig.colorbar(plot, cax=cbar_ax)
        ax.set_title('Percent Cover: {:.2f}%'.format(percent_cover))
        plt.savefig(os.path.abspath(os.path.join(self.weather_directory, r'cloud-img-small.png')))
        # Be really careful about closing up everything so as not to cause any memory leaks
        plt.clf()
        plt.cla()
        plt.close('all')
        if not isinstance(self.plot_lock, type(None)):
            self.plot_lock.release()
        img.close()
        img_small.close()
        if percent_cover >= self.config_dict.cloud_cover_limit:
            return True
        else:
            return False
