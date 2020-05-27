import math
from main.common.util import time_utils

def convert_degrees_to_radians(Degrees):    #degrees may be a list with multiple values to convert
    if type(Degrees) is list:   
        result = []
        for element in Degrees:
            result.append(element*math.pi/180)
        return result
    else:
        return (Degrees*math.pi/180)

def convert_radians_to_degrees(Radians):    #radians may be a list with multiple values to convert
    if type(Radians) is list:    
        result = []
        for element in Radians:
            result.append(element*180/math.pi)
        return result
    else:
        return (Radians*180/math.pi)

def get_dec_and_hour_angle_from_AltAz(azimuth, altitude, latitude):    #Input in degrees
    (azimuth_r, altitude_r, latitude_r) = convert_degrees_to_radians([azimuth, altitude, latitude])
    dec_r = math.asin(math.sin(altitude_r)*math.sin(latitude_r)+math.cos(altitude_r)*math.cos(latitude_r)*math.cos(azimuth_r))
    HA_r = math.acos((math.sin(altitude_r) - math.sin(latitude_r)*math.sin(dec_r))/(math.cos(latitude_r)*math.cos(dec_r)))
    if math.sin(azimuth_r) > 0:
        HA_r = 2*math.pi - HA_r
    (dec, HA) = convert_radians_to_degrees([dec_r, HA_r])
    return (dec, HA)
    
def convert_AltAz_to_RaDec(azimuth, altitude, latitude, longitude, time):
    LST = time_utils.get_local_sidereal_time(longitude, time)
    LST = LST*15
    (dec, HA) = get_dec_and_hour_angle_from_AltAz(azimuth, altitude, latitude)
    ra = (LST - HA)/15
    while ra < 0:
        ra += 24
    while ra > 24:
        ra -= 24
    return (ra, dec)

def convert_RaDec_to_AltAz(ra, dec, latitude, longitude, time):
    LST = time_utils.get_local_sidereal_time(longitude, time)
    HA = (LST - ra)*15
    while HA < 0:
        HA += 360
    while HA > 360:
        HA -= 360
    (dec_r, latitude_r, longitude_r, HA_r) = convert_degrees_to_radians([dec, latitude, longitude, HA])
    alt_r = math.asin(math.sin(dec_r)*math.sin(latitude_r)+math.cos(dec_r)*math.cos(latitude_r)*math.cos(HA_r))
    az_r = math.acos((math.sin(dec_r) - math.sin(alt_r)*math.sin(latitude_r))/(math.cos(alt_r)*math.cos(latitude_r)))
    if math.sin(HA_r) > 0:
        az_r = 2*math.pi - az_r
    (az, alt) = convert_radians_to_degrees([az_r, alt_r])
    return (az, alt)
    
    