import tkinter as tk
import time
import json
import os


def box_labels():
    """
    Description
    -----------
    Labels for each input box

    """
    tk.Label(master, text='Target Name').grid(row=0)
    tk.Label(master, text='Target RA').grid(row=1)
    tk.Label(master, text='Target DEC').grid(row=2)
    tk.Label(master, text='Observation Start Time').grid(row=3)
    tk.Label(master, text='Observation End Time').grid(row=4)
    tk.Label(master, text='Filter(s)').grid(row=5)
    tk.Label(master, text='Number of Exposures').grid(row=6)
    tk.Label(master, text='Exposure Time').grid(row=7)


def exampletxt():
    """
    Description
    -----------
    Example text for each box, showing
    possible formatting options

    """
    tk.Label(master, text='Ex: TOI1234-01').grid(row=0, column=2)
    tk.Label(master, text='Ex: 04:52:53.6698, 04h52m53.67s, 04 52 53.67').grid(row=1, column=2)
    tk.Label(master, text='Ex: -05:27:09.702, -05d27m09.70s, -05 27 09.70').grid(row=2, column=2)
    tk.Label(master, text='Ex: 2020-07-03 10:00:00 (Must be in 24hrs local time)').grid(row=3, column=2)
    tk.Label(master, text='Ex: 2020-07-03 23:00:00 (Must be in 24hrs local time)').grid(row=4, column=2)
    tk.Label(master, text='Can be single filter or list. (clr, uv, b, v, r, ir, Ha)').grid(row=5, column=2)
    tk.Label(master, text='Number of science exposures to be taken per filter').grid(row=6, column=2)
    tk.Label(master, text='Exposure time in seconds for each science image').grid(row=7, column=2)
    tk.Label(master, text='Enable self guiding').grid(row=8, column=2)
    tk.Label(master, text='Enable 3rd party guiding').grid(row=9, column=2)
    tk.Label(master, text='Cycle filter after each science image').grid(row=10, column=2)


def quit_func():
    """
    Description
    -----------
    Defines the function for the quit button,
    saves the inputted text then closes the window
    """
    savetxt()
    master.quit()


def dst_check():
    """
    Description
    -----------
    Checks if the current time is in daylight savings or not

    Returns
    -------
    dst : STR
        Timezone offset from UTC, if daylight savings, offset is -04:00, else -05:00.

    """
    
    if time.localtime().tm_isdst == 1:
        dst = '-04:00'
    else:
        dst = '-05:00'
    return dst

    
def truefalse_check():
    """
    Description
    -----------
    Takes the integers returned by the checkboxes and converts them into strings for .json file

    Returns
    -------
    self_guide_var : STR
        Whether or not to activate self_guide, default is true.
    guide_var : STR
        Whether or not to activate outside guiding, default is false.
    cycle_filter_var : STR
        Whether or not to cycle filter after every image, default is false.

    """
    if self_guide.get() == 1:
        self_guide_var = 'true'
    else:
        self_guide_var = 'false'
    if guide.get() == 1:
        guide_var = 'true'
    else:
        guide_var = 'false'
    if cycle_filter.get() == 1:
        cycle_filter_var = 'true'
    else:
        cycle_filter_var = 'false'
        
    return self_guide_var, guide_var, cycle_filter_var


def filter_split():
    """
    Description
    -----------
    Formats inputted filters correctly

    Returns
    -------
    i : STR
        Properly formatted filter(s).

    """
    j = filter_.get()
    k = j.replace(' ', '')
    i = k.split(",")
    if len(i) == 1:
        i = '\"{}\"'.format(j)
    else:
        i = json.dumps(i)
    return i


def savetxt():
    """
    Description
    -----------
    Saves the text to .json file in proper format

    Returns
    -------
    None.

    """
    dst = dst_check()
    self_guide_var, guide_var, cycle_filter_var = truefalse_check()
    i = filter_split()
    current_path = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(current_path, r'{}.json'.format(name.get())), 'w+') as f:
        f.write('{\"type\": \"observation_ticket\",')
        f.write('\n\"details\":{')
        f.write('\n\t\"name\": \"{}\",'.format(name.get()))
        f.write('\n\t\"ra\": \"{}\",'.format(ra.get()))
        f.write('\n\t\"dec\": \"{}\",'.format(dec.get()))
        f.write('\n\t\"start_time\": \"{}{}\",'.format(start_time.get(), dst))
        f.write('\n\t\"end_time\": \"{}{}\",'.format(end_time.get(), dst))
        f.write('\n\t\"filter\": {},'.format(i))
        f.write('\n\t\"num\": {},'.format(n_exposures.get()))
        f.write('\n\t\"exp_time\": {},'.format(exposure_time.get()))
        f.write('\n\t\"self_guide\": {},'.format(self_guide_var))
        f.write('\n\t\"guide\":{},'.format(guide_var))
        f.write('\n\t\"cycle_filter\": {}'.format(cycle_filter_var))
        f.write('\n\t}\n}')


master = tk.Tk()
# Creates window
master.title('Observation Ticket Creator')
master.geometry('550x300')

box_labels()
exampletxt()

# Creates the input text boxes
name = tk.Entry(master)
ra = tk.Entry(master)
dec = tk.Entry(master)
start_time = tk.Entry(master)
end_time = tk.Entry(master)
filter_ = tk.Entry(master)
n_exposures = tk.Entry(master)
exposure_time = tk.Entry(master)

# Creates variables for check buttons
self_guide = tk.IntVar()
guide = tk.IntVar()
cycle_filter = tk.IntVar()

# Creates check buttons
self_guide.set(1)
b1 = tk.Checkbutton(master, text='Self Guide', onvalue=1, offvalue=0, variable=self_guide)
b1.grid(row=8, column=1)
b2 = tk.Checkbutton(master, text='Guide', onvalue=1, offvalue=0, variable=guide)
b2.place(x=147, y=190)
b3 = tk.Checkbutton(master, text='Cycle Filter', onvalue=1, offvalue=0, variable=cycle_filter)
b3.place(x=147, y=212)

# Places text boxes in the window
name.grid(row=0, column=1)
ra.grid(row=1, column=1)
dec.grid(row=2, column=1)
start_time.grid(row=3, column=1)
end_time.grid(row=4, column=1)
filter_.grid(row=5, column=1)
n_exposures.grid(row=6, column=1)
exposure_time.grid(row=7, column=1)


# Creates Quit and Apply buttons

quit_ = tk.Button(master, text='Quit', command=quit_func)
apply = tk.Button(master, text='Apply', command=savetxt)

# Places the buttons in the window
quit_.place(x=200, y=250)
apply.place(x=235, y=250)

master.mainloop()
