# 1 C:\Users\GMU Observtory1\anaconda3\envs\omegalambda_env\pythonw.exe
import tkinter as tk
import time
import json
import os
import requests
import datetime
import csv
import pandas

# Loads the urls and passwords needed from url_config.json
current_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(current_directory, 'url_config.json')) as f:
    url_dict = json.load(f)
    exofop_page = url_dict['Transit_Site']


def box_labels():
    """
    Description
    -----------
    Labels for each input box

    """
    tk.Label(master, text='Target Name').grid(row=2)
    tk.Label(master, text='Target RA').grid(row=3)
    tk.Label(master, text='Target DEC').grid(row=4)
    tk.Label(master, text='Observation Start Time').grid(row=5)
    tk.Label(master, text='Observation End Time').grid(row=6)
    tk.Label(master, text='Filter(s)').grid(row=7)
    tk.Label(master, text='Number of Exposures').grid(row=8)
    tk.Label(master, text='Exposure Time(s)').grid(row=9)


def exampletxt():
    """
    Description
    -----------
    Example text for each box, showing
    possible formatting options

    """
    tk.Label(master, text='Ex: TOI1234-01').grid(row=2, column=2)
    tk.Label(master, text='Ex: 04:52:53.6698, 04h52m53.67s, 04 52 53.67').grid(row=3, column=2)
    tk.Label(master, text='Ex: -05:27:09.702, -05d27m09.70s, -05 27 09.70').grid(row=4, column=2)
    tk.Label(master, text='Ex: 2020-07-03 10:00:00 (Must be in 24hrs local time)').grid(row=5, column=2)
    tk.Label(master, text='Ex: 2020-07-03 23:00:00 (Must be in 24hrs local time)').grid(row=6, column=2)
    tk.Label(master, text='Can be single filter or list. (clr, uv, b, v, r, ir, Ha)').grid(row=7, column=2)
    tk.Label(master, text='Number of science exposures to be taken').grid(row=8, column=2)
    tk.Label(master, text='Exposure time in seconds for each science image').grid(row=9, column=2)
    tk.Label(master, text='Enable self guiding').grid(row=10, column=2)
    tk.Label(master, text='Enable 3rd party guiding').grid(row=11, column=2)
    tk.Label(master, text='Cycle filter after each science image').grid(row=12, column=2)


def quit_func():
    """
    Description
    -----------
    Defines the function for the quit button,
    saves the inputted text then closes the window
    """
    savetxt()
    master.quit()


def clear_box():
    '''
    Description
    -----------
    Clears the box text in the widget
    '''
    box_list = [name, ra, dec, start_time, end_time, filter_, n_exposures, exposure_time]
    for box in box_list:
        box.delete(0, 'end')


def check_toi():
    '''
    Description
    -----------
    Checks to see if a target has been selected, and if so,
    displays it on the widget

    '''
    global info_directory
    savefile = requests.get(url=url_dict['Google-Sheet'])
    current_directory = os.path.abspath(os.path.dirname(__file__))
    info_directory = os.path.join(current_directory, r'toi_info')
    if not os.path.exists(info_directory):
        os.mkdir(info_directory)

    open(os.path.abspath(os.path.join(info_directory, 'google.csv')), 'wb').write(savefile.content)
    start_date = datetime.date.today()
    toi_tonight = None
    with open(os.path.abspath(os.path.join(info_directory, 'google.csv')), 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if row[0] == str(start_date):
                toi_tonight = row[2]
    if toi_tonight:
        tk.Label(master, text='Tonights TOI is {}'.format(toi_tonight), font=('Courier', 12)).grid(row=0, column=1)
    else:
        tk.Label(master, text='No target specified for tonight', font=('Courier', 12)).grid(row=0, column=1)


def target_grab():
    '''
    Description
    -----------
    Collects and fills in the target info based on the nights target
    in the google doc file
    Returns
    -------

    '''
    if selection.get() != 'Observation List':
        input_info = selection.get().split(': ')
        clear_box()
        start_date = datetime.datetime.strptime(input_info[0], '%Y-%m-%d').date()
        target_toi = input_info[1]
        google_sheet = pandas.read_csv(os.path.abspath(os.path.join(info_directory, 'google.csv')))

        for x in range(0, len(google_sheet['NoD'])):
            if str(start_date) == str(google_sheet['NoD'][x]) and str(google_sheet['Transit'][x]) == target_toi:
                obs_start = str(google_sheet['Start'][x])
                obs_end = str(google_sheet['End'][x])
                filter_input = str(google_sheet['Filter'][x])
                exposure = str(google_sheet['Exp'][x])

        toi = target_toi.split(' ')[1]
        if os.path.exists(os.path.abspath(os.path.join(info_directory, 'info_chart.csv'))):
            tbl_page = requests.get(exofop_page)
            with open(os.path.abspath(os.path.join(info_directory, 'info_chart.csv')), 'wb+') as f:
                f.write(tbl_page.content)

        info_csv = pandas.read_csv(os.path.abspath(os.path.join(info_directory, 'info_chart.csv')))
        ra_coord = None
        dec_coord = None
        for y in range(len(info_csv['TOI'])):
            if str(info_csv['TOI']) == toi:
                raw_coords = str(info_csv['coords(J2000)'][y]).split(' ')
                ra_coord = raw_coords[0]
                dec_coord = raw_coords[1]
                break

        x = datetime.datetime.strptime(obs_start, '%H:%M')
        time_s = datetime.datetime.strftime(x, '%H:%M:%S')
        xx = datetime.datetime.strptime(obs_end, '%H:%M')
        time_e = datetime.datetime.strftime(xx, '%H:%M:%S')

        if x.hour <= 12:
            day_start = str(start_date + datetime.timedelta(days=1))
        else:
            day_start = str(start_date)
        if xx.hour <= 12:
            day_end = str(start_date + datetime.timedelta(days=1))
        else:
            day_start = str(start_date)
        # all the information for the target
        begin = '{} {}'.format(day_start, time_s)
        end = '{} {}'.format(day_end, time_e)
        tonight_toi = target_toi.replace(r' ', r'_')
        exposure = exposure.replace('s', '')
        filter_input = str(filter_input)
        num_exposures = 9999

        # Inserts the target info into the text boxes
        name.insert(10, str(tonight_toi))
        ra.insert(10, str(ra_coord))
        dec.insert(10, str(dec_coord))
        start_time.insert(10, str(begin))
        end_time.insert(10, str(end))
        filter_.insert(10, str(filter_input))
        n_exposures.insert(10, str(num_exposures))
        exposure_time.insert(10, str(exposure))


def create_list():
    '''
    Description
    -----------
    Generates a list of the observations listed in the google sheet
    ex: (YYYY-MM-DD, TOI 1234.01)

    Returns
    -------
    future_toi_list: LIST
        List of targets in list format. Ex: YYYY-MM-DD: TOI 1234.01
    '''
    current_date = datetime.date.today()
    num = 0
    future_toi_list = []
    sheet = pandas.read_csv(os.path.abspath(os.path.join(info_directory, 'google.csv')))

    for x in range(0, len(sheet)):
        if num < 11 and str(sheet['Target'][x]) != 'nan' and str(
                sheet['NoD'][x]) != 'nan':  # There might be empty date spaces at the end of the csv
            row_date = datetime.datetime.strptime(str(sheet['NoD'][x]), '%Y-%m-%d').date()
            if row_date >= current_date and sheet['Target'][x] != 'NaN':
                future_toi_list.append('{}: {}'.format(row_date, sheet['Target'][x]))
                num += 1
    return future_toi_list


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
    return '-04:00' if time.localtime().tm_isdst == 1 else '-05:00'


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
    self_guide_var = 'true' if self_guide.get() == 1 else 'false'
    guide_var = 'true' if guide.get() == 1 else 'false'
    cycle_filter_var = 'true' if cycle_filter.get() == 1 else 'false'

    return self_guide_var, guide_var, cycle_filter_var


def list_split(entry):
    """
    Description
    -----------
    Formats inputted filters correctly

    Parameters
    ----------
    entry : tk.Entry
        Which entry box to parse.

    Returns
    -------
    i : STR
        Properly formatted filter(s).

    """
    i = entry.get().replace(' ', '').split(",")
    if entry == exposure_time:
        i = [float(t) for t in i] if len(i) > 1 else float(i[0])
    elif entry == filter_:
        i = json.dumps([ii if ii == 'Ha' else ii.lower() for ii in i]) if len(i) > 1 else '\"{}\"'.format(
            i[0] if i[0] == 'Ha' else i[0].lower())
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
    i = list_split(filter_)
    j = list_split(exposure_time)
    current_path = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(current_path, r'{}.json'.format(name.get())), 'w+') as f:
        f.write('{\"type\": \"observation_ticket\",')
        f.write('\n\"details\": {')
        f.write('\n\t\"name\": \"{}\",'.format(name.get()))
        f.write('\n\t\"ra\": \"{}\",'.format(ra.get()))
        f.write('\n\t\"dec\": \"{}\",'.format(dec.get()))
        f.write('\n\t\"start_time\": \"{}{}\",'.format(start_time.get(), dst))
        f.write('\n\t\"end_time\": \"{}{}\",'.format(end_time.get(), dst))
        f.write('\n\t\"filter\": {},'.format(i))
        f.write('\n\t\"num\": {},'.format(n_exposures.get()))
        f.write('\n\t\"exp_time\": {},'.format(j))
        f.write('\n\t\"self_guide\": {},'.format(self_guide_var))
        f.write('\n\t\"guide\": {},'.format(guide_var))
        f.write('\n\t\"cycle_filter\": {}'.format(cycle_filter_var))
        f.write('\n\t}\n}')


master = tk.Tk()
# Creates window
master.title('Observation Ticket Creator')
master.geometry('800x380')

box_labels()
exampletxt()
check_toi()
toi_list = create_list()

# Creates and places dropdown menu
selection = tk.StringVar()
selection.set('Observation List')
obs_list = tk.OptionMenu(master, selection, *toi_list).grid(row=1, column=1)

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
b1.grid(row=10, column=1)
b2 = tk.Checkbutton(master, text='Guide', onvalue=1, offvalue=0, variable=guide)
b2.grid(row=11, column=1)
b3 = tk.Checkbutton(master, text='Cycle Filter', onvalue=1, offvalue=0, variable=cycle_filter)
b3.grid(row=12, column=1)

# Places text boxes in the window
name.grid(row=2, column=1)
ra.grid(row=3, column=1)
dec.grid(row=4, column=1)
start_time.grid(row=5, column=1)
end_time.grid(row=6, column=1)
filter_.grid(row=7, column=1)
n_exposures.grid(row=8, column=1)
exposure_time.grid(row=9, column=1)

# Creates Quit, Apply, Clear buttons

select = tk.Button(master, text='Select', command=target_grab)
quit_ = tk.Button(master, text='Quit', command=quit_func)
apply = tk.Button(master, text='Apply', command=savetxt)
clear = tk.Button(master, text='Clear', command=clear_box)

# Places the buttons in the window
quit_.place(x=220, y=350)
apply.place(x=255, y=350)
clear.place(x=298, y=350)
select.place(x=350, y=23)

master.mainloop()
