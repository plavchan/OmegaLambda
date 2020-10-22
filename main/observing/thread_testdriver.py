from condition_checker import Conditions
from controller.thread_monitor import Monitor

con = Conditions()
mon = Monitor()

con.start()
mon.start()
mon.monitor_run()