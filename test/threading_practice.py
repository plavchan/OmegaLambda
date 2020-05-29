#Threading Practice
import threading
import keyboard
import time
import os
'''
Key = threading.Event()

def printer(text):
    while not Key.isSet():
        print(text)
        time.sleep(1)
        
def checker():
    while not Key.isSet():
        if keyboard.is_pressed('a'):
            Key.set()

Thread1 = threading.Thread(target=printer, args=('Hello, world!',))
Thread2 = threading.Thread(target=checker)

Thread1.start()
Thread2.start()
'''
import win32com.client
from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader

try: global_config = ObjectReader(Reader(r'C:\Users\GMU Observtory1\-omegalambda\config\parameters_config.json'))
except: print('ERROR: Error initializing global config object')
else: print('Global config object initialized')



def take_images(num, exp_time, filter, path):
    camera = win32com.client.Dispatch("MaxIm.CCDCamera")
    for i in range(num):
        name = "test_{}.fits".format(i + 1)
        path = os.path.join(path, name)
        camera.Expose(exp_time, 1, filter)
        

image_thread = threading.Thread(target=take_images, args=(3, 2, "r", r'H:\Observatory Files\Observing Sessions\2020_Data\20200529'))
image_thread.start()