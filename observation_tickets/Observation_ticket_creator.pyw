import tkinter as tk


def box_labels():
    tk.Label(master, text = 'Target Name').grid(row = 0)
    tk.Label(master, text = 'Target RA').grid(row = 1)
    tk.Label(master, text = 'Target DEC').grid(row = 2)
    tk.Label(master, text = 'Observation Start Time').grid(row = 3)
    tk.Label(master, text = 'Observation End Time').grid(row = 4)
    tk.Label(master, text = 'Filter(s)').grid(row = 5)
    tk.Label(master, text = 'Number of Exposures').grid(row = 6)
    tk.Label(master, text = 'Exposure Time').grid(row = 7)
    tk.Label(master, text = 'Self Guide').grid(row = 8)
    tk.Label(master, text = 'Guide').grid(row = 9)
    tk.Label(master, text = 'Cycle Filter').grid(row = 10)

def exampletxt():
    tk.Label(master, text = 'Ex: TOI1234-01').grid(row = 0, column = 2)
    tk.Label(master, text = 'Ex: 04:52:53.6698').grid(row = 1, column = 2)
    tk.Label(master, text = 'Ex: -05:27:09.702').grid(row = 2, column = 2)
    tk.Label(master, text = 'Ex: 2020-07-03 10:00:00-04:00').grid(row = 3, column = 2)
    tk.Label(master, text = 'Ex: 2020-07-03 23:00:00-04:00').grid(row = 4, column = 2)
    tk.Label(master, text = 'Can be single filter or list. ie: \"r\" or [\"r\", \"b\", \"uv\"]').grid(row = 5, column = 2)
    tk.Label(master, text = 'Number of science exposures to be taken per filter').grid(row = 6, column = 2)
    tk.Label(master, text = 'Exposure time in seconds for each science image').grid(row = 7, column = 2)
    tk.Label(master, text = '(true/false)** Enable self guiding').grid(row = 8, column = 2)
    tk.Label(master, text = '(true/false)** Enable 3rd party guiding').grid(row = 9, column = 2)
    tk.Label(master, text = '(true/false)** Cycle filter after each science image').grid(row = 10, column = 2)
    tk.Label(master, text = '** MUST BE IN LOWERCASE').grid(row = 11, column = 2)
    

def box_fill():
    self_guide.insert(10, 'true')
    guide.insert(10, 'false')
    cycle_filter.insert(10, 'false')



    
    
def savetxt():
    with open(r'C:/Users/GMU Observtory1/-omegalambda/observation_tickets/{}.json'.format(name.get()), 'w+') as f:
        f.write('{\"type\": \"observation ticket\",')
        f.write('\n\"details\":{')
        f.write('\n\t\"name\": \"{}\",'.format(name.get()))
        f.write('\n\t\"ra\": \"{}\",'.format(ra.get()))
        f.write('\n\t\"dec\": \"{}\",'.format(dec.get()))
        f.write('\n\t\"start_time\": \"{}\",'.format(start_time.get()))
        f.write('\n\t\"end_time\": \"{}\",'.format(end_time.get()))
        f.write('\n\t\"filter\": {},'.format(filter_.get()))
        f.write('\n\t\"num\": {},'.format(n_exposures.get()))
        f.write('\n\t\"exp_time\": {},'.format(exposure_time.get()))
        f.write('\n\t\"self_guide\": {},'.format(self_guide.get()))
        f.write('\n\t\"guide\":{},'.format(guide.get()))
        f.write('\n\t\"cycle_filter\": {}'.format(cycle_filter.get()))
        f.write('\n\t}\n}')
        


    
     
master = tk.Tk()

master.title('Observation Ticket Creator')
master.geometry('550x300')

box_labels()
exampletxt()



name = tk.Entry(master)
ra = tk.Entry(master)
dec = tk.Entry(master)
start_time = tk.Entry(master)
end_time = tk.Entry(master)
filter_ = tk.Entry(master)
n_exposures = tk.Entry(master)
exposure_time = tk.Entry(master)
self_guide = tk.Entry(master)
guide = tk.Entry(master)
cycle_filter = tk.Entry(master)

name.grid(row = 0, column = 1)
ra.grid(row = 1, column = 1)
dec.grid(row = 2, column = 1)
start_time.grid(row = 3, column = 1)
end_time.grid(row = 4, column = 1)
filter_.grid(row = 5, column = 1)
n_exposures.grid(row = 6, column = 1)
exposure_time.grid(row = 7, column = 1)
self_guide.grid(row = 8, column = 1)
guide.grid(row = 9, column = 1)
cycle_filter.grid(row = 10, column = 1)

box_fill()


quit_ = tk.Button(master, text = 'Quit', command = master.quit)
apply = tk.Button(master, text = 'Apply', command = savetxt)
quit_.place(x = 200, y = 250)
apply.place(x = 235, y = 250)

master.mainloop()