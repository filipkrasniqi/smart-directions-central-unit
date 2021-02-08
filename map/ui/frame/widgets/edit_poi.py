import tkinter as tk

'''
UI associated with the update of a PoI.
'''
class EditPoI(tk.Toplevel):
    def __init__(self, master, poi):
        tk.Toplevel.__init__(self, master=master)
        self.wm_title("Edit point of interest")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.wm_geometry("+%d+%d" % (poi.getCoordinates()[0] + 20, poi.getCoordinates()[1] + 57))

        self.poi = poi

        self.name = tk.Entry(self)
        self.name.grid(column=0, row=0)

        self.cancel = tk.Button(self, text="Go back", command=self.goBack)
        self.cancel.grid(column=0, row=2)

        self.save = tk.Button(self, text="Save", command=self.save)
        self.save.grid(column=0, row=3)

        self.__initUI()

    def __initUI(self):
        self.name.insert(0, self.poi.name)

    def on_closing(self):
        self.destroy()

    def save(self):
        self.poi.name = self.name.get()
        self.destroy()

    def goBack(self):
        self.destroy()