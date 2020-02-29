from main.controller.camera import Camera

camera_object = Camera()
#camera_object.check_connection()


camera_object.expose(2, 4, r'c\users\gmuobservatory\documents\observing sessions\2020_data\testimage.fits', type="light")

#NEEDS TESTING