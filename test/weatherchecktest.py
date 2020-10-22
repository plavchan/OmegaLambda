import requests
import re
"""
url = 'https://weather.com/weather/hourbyhour/' + \
                                  'l/e8321c2fb1f8234f40bf92ce494921d94e657d54cc2c01f1882755e04b761dee'


s = requests.Session()
weather_request = s.get(url, headers={'User-Agent': 'Mozilla/5.0'})

with open(r'C:\ Users\GMU Observtory1\-omegalambda\resources\weather_status\weather.txt', 'w') as \
        file:
    # Writes the html code to a text file
    file.write(str(weather_request.content))

with open(r'C:\ Users\GMU Observtory1\-omegalambda\resources\weather_status\weather.txt', 'r') as \
        file:
    # Reads the text file to find humidity, wind, rain
    text = file.read()
    humidity = re.search(r'<span data-testid="PercentageValue" class="_-_-components-src-molecule-' +
                         r'DaypartDetails-DetailsTable-DetailsTable--value--2YD0-">(.+?)</span>',
                         text).group(1)
    wind = re.search(r'<span data-testid="Wind" class="_-_-components-src-atom-WeatherData-Wind-Wind' +
                     r'--windWrapper--3Ly7c undefined">(.+?)</span>', text).group(1)
    rain = re.search(r'<span data-testid="PercentageValue">(.+?)</span>', text).group(1)

    humidity = float(humidity.replace('%', ''))
    test_wind = re.search(r'[+-]?\d+\.\d+', wind)
    if test_wind:
        wind = float(test_wind.group())
    else:
        wind = int(re.search(r'[+-]?\d', wind).group())
    rain = float(rain.replace('%', ''))

print('Humidity: {}'.format(humidity))
print('Wind: {}'.format(wind))
print('Rain: {}'.format(rain))
"""
from ..main.observing.condition_checker import Conditions
from ..main.common.IO.json_reader import Reader
from ..main.common.datatype.object_reader import ObjectReader
import time

cd = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))

c = Conditions()
c.start()
time.sleep(30)
c.stop.set()