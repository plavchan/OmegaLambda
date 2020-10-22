import win32com.client

x = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
x.DeviceType = "Camera"
driver = x.Choose(None)
print("The driver is" + driver)

win32com.client.Dispatch(driver)
