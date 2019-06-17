def CameraLogging(self):
    file=open("Logging.text","w+") #creates a file that allows Write and Read. "r+" allows Read and Write
    for i in range(100):
        file.write((self.camera.CameraState)(i+1))
    file.close()
