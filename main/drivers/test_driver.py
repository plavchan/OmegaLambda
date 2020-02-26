from main.controller.camera import Camera

camera_object = Camera()
#camera_object.check_connection()
#camera_object.coolerSet()

camera_object.expose(2, 4, r'c\users\gmuobservatory\documents\observing sessions\2020_data\image.fits', type="light")

#NEEDS TESTING