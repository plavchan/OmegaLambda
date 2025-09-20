# 1 C:\Users\GMU Observtory1\anaconda3\envs\omegalambda_env\pythonw.exe
import tkinter as tk
import gc
from threading import Thread
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
    tk.Label(master, text='Camera').grid(row=10)


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
    tk.Label(master, text="Camera to be used for observation: CCD or NIR").grid(row=10, column=2)
    tk.Label(master, text='Enable self guiding. Disabled if satellite tracking is enabled.').grid(row=11, column=2)
    tk.Label(master, text='Enable 3rd party guiding').grid(row=12, column=2)
    tk.Label(master, text='Cycle filter after each science image').grid(row=13, column=2)
    tk.Label(master, text='Enable automatic coarse focus').grid(row=14, column=2)
    tk.Label(master, text='Enable satellite tracking').grid(row=15, column=2)
    tk.Label(master, text="Satellite tracking mode. 0: Disabled\n1: Sidereal tracking; 2: Satellite tracking; 3: Half-rate tracking").grid(row=16, column=2)


def quit_func():
    """
    Description
    -----------
    Defines the function for the quit button,
    saves the inputted text then closes the window
    """
    if dialog:
        time.sleep(2)
        dialog.join()
    if dialog_2:
        dialog_2.join()
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
    global info_directory, google_path, SATELLITES
    current_directory = os.path.abspath(os.path.dirname(__file__))
    info_directory = os.path.join(current_directory, r'toi_info')
    if not os.path.exists(info_directory):
        os.mkdir(info_directory)

    google_path = os.path.abspath(os.path.join(info_directory, 'google.csv'))
    savefile = requests.get(url=url_dict['Google-Sheet'], timeout=30)
    open(google_path, 'wb').write(savefile.content)
    start_date = datetime.date.today()
    toi_tonight = None
    with open(google_path, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if row[0] == str(start_date):
                toi_tonight = row[2]
    if toi_tonight:
        tk.Label(master, text="Tonight's target is {}".format(toi_tonight), font=('Courier', 12)).grid(row=0, column=1)
    else:
        tk.Label(master, text='No target specified for tonight', font=('Courier', 12)).grid(row=0, column=1)

    # Satellites
    satellites_path = os.path.abspath(os.path.join(info_directory, 'satellites.txt'))

    # Celestrak has a very tight rate limit
    if os.path.exists(satellites_path) and datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(satellites_path)) < datetime.timedelta(hours=12):
        with open(satellites_path, 'r') as f:
            SATELLITES = {line.strip() for line in f}
    else:
        tles_url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"

        dialog = DialogThread("Downloading satellite info", "Please wait...retrieving satellite information.\nThis may take up to 30 seconds.")
        tles = requests.get(tles_url, timeout=30)

        SATELLITES = set()
        for line in tles.text.splitlines():
            if line[0] not in ('1', '2'):
                line = line.strip()
                SATELLITES.add(line.upper())
                if '(' in line:
                    SATELLITES.add(line.split('(')[0].strip().upper())

        with open(satellites_path, 'w') as f:
            f.write('\n'.join(sorted(SATELLITES)))
        
        dialog.join()


class DialogThread(Thread):
    def __init__(self, title, message):
        self.title = title
        self.message = message
        self.stop = False
        super().__init__()
        self.start()

    def run(self):
        self.dialog = tk.Tk()
        self.dialog.title(self.title)
        self.dialog.overrideredirect(True)
        self.dialog.geometry('+%d+%d' % (self.dialog.winfo_screenwidth() / 5 - 200, self.dialog.winfo_screenheight() / 5 - 100))

        label = tk.Label(self.dialog, text=self.message)
        label.pack(padx=20, pady=20)
        
        while not self.stop:
            self.dialog.update()
            time.sleep(0.1)
            
        self.dialog.destroy()
        self.dialog = None
        gc.collect()
    
    def join(self):
        self.stop = True
        super().join()

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
        target = input_info[1]
        google_sheet = pandas.read_csv(google_path)

        x = int(target.split('_')[-1][1:])
        target_name = str(google_sheet['Target'][x])
        obs_start = str(google_sheet['Start'][x])
        obs_end = str(google_sheet['End'][x])
        filter_input = str(google_sheet['Filter'][x])
        exposure = str(google_sheet['Exp'][x])
        if "Camera" in google_sheet.columns:
            selected_cam = str(google_sheet['Camera'][x])
        else:
            selected_cam = "CCD"
        if "Satellite Tracking" in google_sheet.columns:
            satellite_tracking_data = int(google_sheet['Satellite Tracking'][x])
        if "Tracking Mode" in google_sheet.columns:
            tracking_mode_data = int(google_sheet['Tracking Mode'][x])

        toi = target_name
        if toi.startswith('TOI'):
            toi = toi.replace(" ", "").replace("TOI", "")
            target_name = target_name.replace(" ", "").replace(".", "-")
        info_chart_path = os.path.abspath(os.path.join(info_directory, 'info_chart.csv'))
        if not os.path.exists(info_chart_path) or datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(info_chart_path)) > datetime.timedelta(hours=12):
            dialog = DialogThread('Downloading TOI info', 'Please wait...retrieving TOI information.\nThis may take up to 30 seconds.')
            tbl_page = requests.get(exofop_page, timeout=90)
            with open(info_chart_path, 'wb+') as f:
                f.write(tbl_page.content)
            dialog.join()
        info_csv = pandas.read_csv(info_chart_path)
        ra_coord = None
        dec_coord = None
        for y in range(len(info_csv['TOI'])):
            if str(info_csv['TOI'][y]) == toi:
                ra_coord = info_csv['RA'][y]
                dec_coord = info_csv['Dec'][y]
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
            day_end = str(start_date)
        # all the information for the target
        begin = '{} {}'.format(day_start, time_s)
        end = '{} {}'.format(day_end, time_e)

        exposure = exposure.replace('s', '')
        filter_input = str(filter_input)
        num_exposures = 100000

        # Inserts the target info into the text boxes
        name.insert(10, str(target_name))
        ra.insert(10, str(ra_coord))
        dec.insert(10, str(dec_coord))
        start_time.insert(10, str(begin))
        end_time.insert(10, str(end))
        filter_.insert(10, str(filter_input))
        n_exposures.insert(10, str(num_exposures))
        exposure_time.insert(10, str(exposure))
        camera.set(selected_cam)   
        satellite_tracking.set(satellite_tracking_data)
        satellite_tracking_mode.set(tracking_mode_data)
        self_guide.set(0 if satellite_tracking_data else 1)  # Disable self guiding if satellite tracking is enabled


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
    future_toi_list = []
    sheet = pandas.read_csv(google_path)

    for x in range(len(sheet)):
        target = str(sheet['Target'][x])
        if target.startswith("TOI"):
            target = target.replace(r" ", "").replace(r".", "-")
        nod = str(sheet['NoD'][x])
        if target != 'nan' and nod != 'nan':  # There might be empty date spaces at the end of the csv
            row_date = datetime.datetime.strptime(nod, '%Y-%m-%d').date()
            if row_date >= current_date and target != 'NaN':
                enable_sat_tracking = sheet['Satellite Tracking'][x]
                sat_mode = f"_Mode{sheet['Tracking Mode'][x]}" if enable_sat_tracking else ""
                display_name = f"{target}_{sheet['Start'][x]}{sat_mode}_{sheet['Exp'][x]}_{sheet['Filter'][x]}_#{x}"
                future_toi_list.append('{}: {}'.format(row_date, display_name))
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
        i = json.dumps([ii if ii == 'Ha' else ii.lower() for ii in i]) if len(i) > 1 else i[0] if i[0] == 'Ha' else i[0].lower()
    return i


dialog = None
def savetxt():
    """
    Description
    -----------
    Saves the text to .json file in proper format

    Returns
    -------
    None.

    """
    global dialog

    dst = dst_check()
    i = list_split(filter_)
    j = list_split(exposure_time)
    current_path = os.path.abspath(os.path.dirname(__file__))

    if satellite_tracking.get() and name.get().upper() not in SATELLITES:
        if not dialog:
            dialog = DialogThread('Error: Satellite not found', f'Error: the specified satellite "{name.get()}" was not found in the catalog.\nCheck the target name. Try swapping dashes and spaces.')
        return
    elif dialog:
        dialog.join()
        dialog = None

    observation_ticket = {
        "type": "observation_ticket",
        "details": {
            "name": name.get(),
            "ra": None if (r := ra.get()) == "None" else r,
            "dec": None if (d := dec.get()) == "None" else d,
            "start_time": start_time.get() + dst,
            "end_time": end_time.get() + dst,
            "filter": i,
            "num": int(n_exposures.get()),
            "exp_time": j,
            "camera": camera.get(),
            "self_guide": bool(self_guide.get()),
            "guide": bool(guide.get()),
            "cycle_filter": bool(cycle_filter.get()),
            "initial_focus": bool(initial_focus.get()),
            "satellite_tracking": bool(satellite_tracking.get()),
            "satellite_tracking_mode": satellite_tracking_mode.get()
        }
    }

    with open(os.path.join(current_path, selection.get().split(": ")[1].replace(':', '') + ".json"), 'w+') as f:
        json.dump(observation_ticket, f, indent=4)


def save_all():
    """Save all of the targets in the list"""
    for target in toi_list[1:]:
        selection.set(target)
        target_grab()
        savetxt()
        print("Saved target:", target)


dialog_2 = None
def save_all_auto_folders():
    """
    Save all the targets in the list and automatically make folders for the targets in the list. 
    The folders will be named by date: YYYYMMDD
    """
    global dialog_2

    for target in toi_list[1:]:
        selection.set(target)
        target_grab()
        savetxt()
        current_path = os.path.abspath(os.path.dirname(__file__))
        target_name = target.split(": ")[1].replace(':', '')
        target_path = os.path.join(current_path, target_name + ".json")
        with open(target_path, 'r') as f:
            target_info = json.load(f)
        start_time = datetime.datetime.strptime(target_info["details"]["start_time"].replace(dst_check(), ""), "%Y-%m-%d %H:%M:%S")
        if start_time.hour < 12:
            start_time = start_time - datetime.timedelta(days=1)
        folder_name = start_time.strftime("%Y%m%d")
        folder_path = os.path.join(current_path, folder_name)
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)
        if not os.path.exists(os.path.join(folder_path, target_name + ".json")):
            os.rename(target_path, os.path.join(folder_path, target_name + ".json"))
        else:
            os.remove(target_path)
        print("Saved target:", target)
        auto_make_folders["state"] = "disabled"
    
    tonight = datetime.date.today() if datetime.datetime.now().hour >= 12 else datetime.date.today() - datetime.timedelta(days=1)
    command = f"python -m omegalambda run {os.path.join(current_path, tonight.strftime('%Y%m%d'))}".replace("\\", "/")
    master.clipboard_clear()
    master.clipboard_append(command)
    dialog_2 = DialogThread(
        'Saved all targets into folders', 
        f"""All targets have been saved and placed into folders by date.
        The following command to run OmegaLambda on tonight's folder has been copied to the clipboard:
        {command}
        Click Quit to exit the program.
        """
    )


master = tk.Tk()
# Creates window
master.title('Observation Ticket Creator')
master.geometry('1100x600')

box_labels()
exampletxt()
check_toi()
toi_list = create_list()

if not toi_list:
    tk.Label(master, text='No targets found!', font=("Courier 18 bold")).grid(row=14, column=1)
    master.mainloop()
    exit()

# Creates the input text boxes
name = tk.Entry(master)
ra = tk.Entry(master)
dec = tk.Entry(master)
start_time = tk.Entry(master)
end_time = tk.Entry(master)
filter_ = tk.Entry(master)
n_exposures = tk.Entry(master)
exposure_time = tk.Entry(master)

# Creates and places dropdown menu
selection = tk.StringVar()
obs_list = tk.OptionMenu(master, selection, *toi_list).grid(row=1, column=1)

camera = tk.StringVar()
camera_list = tk.OptionMenu(master, camera, 'CCD', 'NIR').grid(row=10, column=1)

satellite_tracking = tk.IntVar()
satellite_tracking_checkbox = tk.Checkbutton(master, text="Satellite Tracking", onvalue=1, offvalue=0, variable=satellite_tracking)
satellite_tracking_checkbox.grid(row=15, column=1)

satellite_tracking_mode = tk.IntVar()
satellite_tracking_mode_options = tk.OptionMenu(master, satellite_tracking_mode, 0, 1, 2, 3)
satellite_tracking_mode_options.grid(row=16, column=1)


# Creates variables for check buttons
self_guide = tk.IntVar()
guide = tk.IntVar()
cycle_filter = tk.IntVar()
initial_focus = tk.IntVar()
initial_focus.set(1)


selection.set(toi_list[0])
toi_list.insert(0, 'Observation List')
target_grab()


# Creates check buttons
b1 = tk.Checkbutton(master, text='Self Guide', onvalue=1, offvalue=0, variable=self_guide)
b1.grid(row=11, column=1)
b2 = tk.Checkbutton(master, text='Guide', onvalue=1, offvalue=0, variable=guide)
b2.grid(row=12, column=1)
b3 = tk.Checkbutton(master, text='Cycle Filter', onvalue=1, offvalue=0, variable=cycle_filter)
b3.grid(row=13, column=1)
b4 = tk.Checkbutton(master, text='Initial Focus', onvalue=1, offvalue=0, variable=initial_focus)
b4.grid(row=14, column=1)

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
saveall = tk.Button(master, text='Save All', command=save_all)
auto_make_folders = tk.Button(master, text='Save All into Folders by Date', command=save_all_auto_folders)
quit_ = tk.Button(master, text='Quit', command=quit_func)
apply = tk.Button(master, text='Apply', command=savetxt)
clear = tk.Button(master, text='Clear', command=clear_box)

# Places the buttons in the window
BOTTOM_Y = 550
quit_.place(x=200, y=BOTTOM_Y)
apply.place(x=270, y=BOTTOM_Y)
clear.place(x=350, y=BOTTOM_Y)
select.place(x=600, y=23)
saveall.place(x=700, y=23)
auto_make_folders.place(x=800, y=23)

master.mainloop()
