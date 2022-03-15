import mttkinter.mtTkinter as tk
import threading

from ..common.IO import config_reader


class Gui(threading.Thread):

    def __init__(self, focus_obj, focusprocedures_obj, focus_toggle):
        """
        Description
        -----------
        Initializes the focus Gui as a subclass of threading.Thread.  Meant to set up a gui running on its own
        thread that can interact with the focuser.

        Parameters
        ----------
        focus_obj:  Focuser
            from focuser_control

        """
        self.focuser = focus_obj
        self.focus_procedures = focusprocedures_obj
        self.focus_toggle = focus_toggle
        self.close_window = threading.Event()

        super(Gui, self).__init__(name='Gui-Th', daemon=True)

    def move_in_cmd(self, amount):
        """
        Parameters
        ----------
        amount: INT
            Steps to move the focuser in by.

        Returns
        -------
        None
        """
        self.focuser.onThread(self.focuser.move_in, amount)
        # self.focuser.adjusting.wait()
        # self.position.set(self.focuser.position)

    def move_out_cmd(self, amount):
        """
        Parameters
        ----------
        amount: INT
            Steps to move the focuser out by.

        Returns
        -------
        None
        """
        self.focuser.onThread(self.focuser.move_out, amount)
        # self.focuser.adjusting.wait()
        # self.position.set(self.focuser.position)

    def abort_cmd(self):
        """
        Description
        -----------
        Aborts any current moves.

        Returns
        -------
        None
        """
        self.focuser.onThread(self.focuser.abort)

    def update_labels(self, root, position, comport_var, move_in, move_out):
        """
        Description
        -----------
        Constantly updates the focus position in the background.  Is kept running by the tkinter main loop.

        Returns
        -------
        None
        """
        position.set(self.focuser.position)
        comport_var.set(self.focuser.comport)
        if self.focus_procedures.focused.isSet() or not self.focus_toggle:
            move_in['state'] = tk.NORMAL
            move_out['state'] = tk.NORMAL
        else:
            move_in['state'] = tk.DISABLED
            move_out['state'] = tk.DISABLED
        if self.close_window.isSet():
            root.destroy()
        else:
            root.after(500, lambda: self.update_labels(root, position, comport_var, move_in, move_out))

    def create_root(self):
        """
        Description
        -----------
        Sets up all the parameters for the gui (text, buttons, entry boxes, etc.)

        Returns
        -------
        root: tk.Tk
            The main Tkinter root application
        position: tk.IntVar
            The integer position variable of the focus mirror.
        comport_var: tk.StringVar
            A string variable detailing the COM port connection info.
        move_in: tk.Button
            A button object for moving the focus inwards.
        move_out: tk.Button
            A button object for moving the focus outwards.
        """
        root = tk.Tk()
        root.title('Ultra Deluxe Focus Control Hub EXTREME')
        root.geometry('430x140')
        root.protocol("WM_DELETE_WINDOW", root.iconify)

        connection_text = tk.Label(root, text='The focuser is connected to: ')
        connection_text.grid(row=1, column=1)
        comport_var = tk.StringVar()
        comport_var.set(self.focuser.comport)
        comport = tk.Label(root, textvariable=comport_var)
        comport.grid(row=1, column=2)

        position = tk.IntVar()
        position.set(self.focuser.position)
        position_msg = tk.Label(root, text='The current position is: ')
        position_msg.grid(row=2, column=1)
        position_text = tk.Label(root, textvariable=position)
        position_text.grid(row=2, column=2)

        delta = tk.IntVar()
        delta.set(config_reader.get_config().initial_focus_delta)
        delta_entry = tk.Entry(root, textvariable=delta, width=5)
        delta_entry.grid(row=3, column=2)
        button_frame = tk.Frame(root)
        move_in = tk.Button(button_frame, text='MOVE IN', state=tk.DISABLED,
                            command=lambda: self.move_in_cmd(delta.get()))
        move_out = tk.Button(button_frame, text='MOVE OUT', state=tk.DISABLED,
                             command=lambda: self.move_out_cmd(delta.get()))
        button_frame.grid(row=3, column=1, sticky="nsew", pady=10, padx=20)
        move_in.pack(side="left")
        move_out.pack(side="right")
        abort = tk.Button(root, text='ABORT', command=self.abort_cmd, width=15)
        abort.grid(row=4, column=1, columnspan=2)

        # Only return the objects that will need updating
        # connection_text, comport, position_msg, position_text, delta, button_frame, and abort do not need explicit updates

        return root, position, comport_var, move_in, move_out

    def run(self):
        """
        Description
        -----------
        Starts the main loop of the gui

        Returns
        -------
        None
        """

        root, position, comport_var, move_in, move_out = self.create_root()
        self.update_labels(root, position, comport_var, move_in, move_out)
        root.mainloop()
        root.quit()
