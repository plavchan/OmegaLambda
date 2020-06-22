from ..controller.hardware import Hardware


'''
1. Camera takes an exposure in observation_run
2. Find & record test star's position in FOV
3. Camera takes another exposure in observation_run
4. Compare test star's new position to its last one
5. If too small, do nothing, keep first position saved (so that when we eventually jog, 
   it is correct for the difference since the first exposure)
6. If big enough, Pulseguide/jog telescope to correct for the difference b/w
   previous (or first) location and current location
7. Make sure dome slaves correctly (should already be taken care of)
'''

class Guider(Hardware):
    
    def __init__(self, camera_obj, telescope_obj):
        self.camera = camera_obj
        self.telescope = telescope_obj
        super(Guider, self).__init__(name='Guider')
        
        #Events/locks go here
        #Idea would be to wait for the last camera.expose from take_images, then call guider.findstars or something to see if a move is necessary
                
    def FindStars(self):  #Find test star position
        pass
    
    def ComparePositions(self):     #Compare positions of 2 exposures and decide to move or not
        pass    