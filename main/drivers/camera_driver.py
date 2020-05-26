from main.controller.camera import Camera
import time


camera_object = Camera()

camera_object.expose(2, 4, r'h:\observatory files\observing sessions\2020_data\testimage.fits', type="light")

'''
while camera_object.Camera.CoolerPower:
    previous = camera_object.Camera.TemperatureSetpoint
    camera_object.coolerAdjust()
    current = camera_object.Camera.TemperatureSetpoint
    if (previous == current                                                                     #setpoint hasn't changed since last check
        and camera_object.Camera.TemperatureSetpoint <= camera_object.Camera.Temperature + 0.1  #The setpoint and actual temp are within 0.2 of each other.
        and camera_object.Camera.TemperatureSetPoint >= camera_object.Camera.Temperature - 0.1
        and camera_object.Camera.ImageReady == True):                                           #Camera isn't currently exposing
        break
    time.sleep(60)
'''

camera_object.Camera.TemperatureSetpoint = 5
camera_object.disconnect()