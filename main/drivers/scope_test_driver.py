from main.controller.telescope import Telescope

scope_obj = Telescope()
scope_obj.telescopeSlew(3.5, 4.5)
scope_obj.park()

'''
import win32com.client      #needed to load COM objects
x = win32com.client.Dispatch("ASCOM.Utilities.Chooser")

x.DeviceType = 'Telescope'
print(x.Choose(None))
'''