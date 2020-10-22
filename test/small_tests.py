# import matplotlib.pyplot as plt
# import threading
#
#
# def make_plot():
#     fig, ax = plt.subplots()
#     ax.plot([1, 2, 3], [4, 5, 6], 'bo:', label='Data')
#     ax.set_xlabel('x-axis')
#     ax.set_ylabel('y-axis')
#     ax.set_title('Super cool data')
#     ax.legend()
#     ax.grid()
#     ax.set_xticks(
#         [0, 1, 2, 3, 4]
#     )
#     ax.set_yticks(
#         [0, 1, 2, 3, 4, 5, 6, 7]
#     )
#     plt.savefig(r'C:/Users/GMU Observtory1/-omegalambda/test/qapplication-plot.png')
#
#
# test_thread = threading.Thread(target=make_plot)
# test_thread.start()
# test_thread.join()
"""
import threading
import time
import queue
import pythoncom
from win32com.client import Dispatch


class testclass(threading.Thread):

    def __init__(self):
        self.hi = 'hi'
        self.bye = 'bye'
        self.q = queue.Queue()
        self.loop_time = 1.0/60
        self.running = threading.Event()
        self.running.set()
        super(testclass, self).__init__()

    def testfunc(self):
        while self.running.isSet():
            print(self.hi)
            print(self.bye)
            time.sleep(1)

    def testfunc2(self, dir, dur):
        try:
            self.tel.PulseGuide(dir, dur)
        except:
            print('oh no!')
        print('Telescope is pulse guiding')

    def onThread(self, function, *args, **kwargs):
        self.q.put((function, args, kwargs))

    def run(self):
        pythoncom.CoInitialize()
        self.tel = Dispatch("ASCOM.SoftwareBisque.Telescope")
        self.tel.Connected = True
        while self.running.isSet():
            try:
                function, args, kwargs = self.q.get(timeout=self.loop_time)
                function(*args, **kwargs)
            except queue.Empty:
                time.sleep(1)
        pythoncom.CoUninitialize()

    def stop(self):
        self.running.clear()


class guidertestclass(threading.Thread):

    def __init__(self, camera, testclass0):
        self.cam = camera
        self.t = testclass0
        self.q = queue.Queue()
        self.loop_time = 1.0/60
        self.running = threading.Event()
        self.running.set()
        super(guidertestclass, self).__init__()

    def guidertestfunc(self, a, b):
        self.t.testfunc2(a, b)

    def onThread(self, function, *args, **kwargs):
        self.q.put((function, args, kwargs))

    def run(self):
        while self.running.isSet():
            try:
                function, args, kwargs = self.q.get(timeout=self.loop_time)
                function(*args, **kwargs)
            except queue.Empty:
                time.sleep(1)

    def stop(self):
        self.running.clear()


tc = testclass()    # telescope class
tc.start()
gc = guidertestclass(0, tc)
gc.start()
time.sleep(2)
gc.onThread(gc.guidertestfunc, 3, 5000)
time.sleep(5)
gc.stop()
tc.stop()

import time
import msvcrt
import sys

def test_func(a, b, c):
    print(a+b+c)

class TimeoutExpired(Exception):
    pass


def input_with_timeout(prompt, timeout, timer=time.monotonic):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    endtime = timer() + timeout
    while timer() < endtime:
        if msvcrt.kbhit():
            return msvcrt.getwche()
        time.sleep(0.04)
    raise TimeoutExpired

if __name__ == '__main__':
    try:
        answer = input_with_timeout(
            "Focuser has failed to produce a good parabolic fit.  Would you like to try again? (y/n) \n"
            "You have 30 seconds to answer; on timeout the program will automatically refocus: ",
            30
        )
        if answer == 'y':
            print('\nalright, here we go')
            test_func(1, 3, 8)
        elif answer == 'n':
            print('\nok, fine')
    except TimeoutExpired:
        print('\noh no! time\'s up')
"""
"""
class HelloThere:
    classvar = 0

    def __init__(self):
        self.instancevar = 'hi'
        self.instantcevar2 = 'bye'

    def changecvar(self):
        self.classvar = 1

if __name__ == '__main__':
    ht = HelloThere()
    ht.changecvar()
    print(HelloThere.classvar)
    print(ht.classvar)
"""

"""
class Foo:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


class Bar(Foo):
    def __init__(self, y, z):
        super().__init__(1, y, z)


if __name__ == '__main__':
    f = Foo(1, 2, 0)
    print(f.x, f.y)
    b = Bar(3, 9)
    print(b.x, b.y, b.z)
"""

import argparse


def cli_run(args):
    awesome_function(args.letter, args.cool)


def awesome_function(a, b):
    print(b)
    if b is True:
        print(f'awesome! you letter was: {a}')
    elif b is False:
        print(f'not cool... your letter was: {a}')


def test():
    parser = argparse.ArgumentParser(description='test cli')
    subparsers = parser.add_subparsers()
    test_driver = subparsers.add_parser('testrun', help='do a test run')
    test_driver.add_argument('letter', nargs=1, help='a letter to print out')
    test_driver.add_argument('--cool', '-c', action='store_false', dest='cool',
                             help='a test true/false option')
    test_driver.set_defaults(func=cli_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    test()