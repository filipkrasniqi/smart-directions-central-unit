from tkinter import Toplevel, Label, LEFT, SOLID
import tkinter as tk

class ToolTip(Toplevel):

    def __init__(self, master, id, text, x, y):
        Toplevel.__init__(self, master=master)
        self.id = id
        self.wm_overrideredirect(1)
        self.wm_geometry("+%d+%d" % (x + 20, y + 57))
        label = tk.Label(self, text=text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def __eq__(self, other):
        return (isinstance(other, ToolTip) and other.id == self.id) or (isinstance(other, str) and other == self.id)