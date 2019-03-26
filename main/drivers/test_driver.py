from camera import Camera                       #the from statement has an error yet still runs

camera_object = Camera("Camera Work")           #Allows access to the Camera class. I still don't understand why "Camera Work" is there.
exposure_time=1                                 #Editable exposure time. Not sure if works with large values.
type=1                                          #Editable exposure type. Input only 1 or 0.
filter=1                                        #Editable exposure filter. filter wheel function has to be implemented for it to work effectively.
camera_object.expose(exposure_time,type,filter) #Sets the expose function's values.

