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
        self.root = self.delta = self.position = self.position_text = None
        self.focuser = focus_obj
        self.focus_procedures = focusprocedures_obj
        self.focus_toggle = focus_toggle

        self.comport_var = self.comport = self.move_in = self.move_out = None
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

    def update_labels(self):
        """
        Description
        -----------
        Constantly updates the focus position in the background.  Is kept running by the tkinter main loop.

        Returns
        -------
        None
        """
        self.position.set(self.focuser.position)
        self.comport_var.set(self.focuser.comport)
        if self.focus_procedures.focused.isSet() or not self.focus_toggle:
            self.move_in['state'] = tk.NORMAL
            self.move_out['state'] = tk.NORMAL
        self.position_text.after(1000, self.update_labels)

    def create_root(self):
        """
        Description
        -----------
        Sets up all the parameters for the gui (text, buttons, entry boxes, etc.)

        Returns
        -------
        None
        """
        self.root = tk.Tk()
        self.root.title('Ultra Deluxe Focus Control Hub EXTREME')
        self.root.geometry('430x140')

        connection_text = tk.Label(self.root, text='The focuser is connected to: ')
        connection_text.grid(row=1, column=1)
        self.comport_var = tk.StringVar()
        self.comport_var.set(self.focuser.comport)
        self.comport = tk.Label(self.root, textvariable=self.comport_var)
        self.comport.grid(row=1, column=2)

        self.position = tk.IntVar()
        self.position.set(self.focuser.position)
        position_msg = tk.Label(self.root, text='The current position is: ')
        position_msg.grid(row=2, column=1)
        self.position_text = tk.Label(self.root, textvariable=self.position)
        self.position_text.grid(row=2, column=2)

        self.delta = tk.IntVar()
        self.delta.set(config_reader.get_config().initial_focus_delta)
        delta_entry = tk.Entry(self.root, textvariable=self.delta, width=5)
        delta_entry.grid(row=3, column=2)
        button_frame = tk.Frame(self.root)
        self.move_in = tk.Button(button_frame, text='MOVE IN', state=tk.DISABLED,
                            command=lambda: self.move_in_cmd(self.delta.get()))
        self.move_out = tk.Button(button_frame, text='MOVE OUT', state=tk.DISABLED,
                             command=lambda: self.move_out_cmd(self.delta.get()))
        button_frame.grid(row=3, column=1, sticky="nsew", pady=10, padx=20)
        self.move_in.pack(side="left")
        self.move_out.pack(side="right")
        abort = tk.Button(self.root, text='ABORT', command=self.abort_cmd, width=15)
        abort.grid(row=4, column=1, columnspan=2)

    def run(self):
        """
        Description
        -----------
        Starts the main loop of the gui

        Returns
        -------
        None
        """

        self.create_root()
        self.update_labels()
        self.root.mainloop()
