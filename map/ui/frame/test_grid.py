import tkinter as tk

from map.elements.planimetry.sd_instance import SmartDirectionInstance
from map.ui.frame.add_building_frame import AddBuilding
from utils.parser import Parser

'''
UI associated with the list of buildings
'''
class TestGrid(tk.Toplevel):
    def __init__(self, root, id_sd, current_sd = None):
        super().__init__(root)
        self.root = root
        self.id_sd_instance = id_sd
        self.sd_instance = current_sd
        if self.sd_instance is None:
            self.sd_instance = SmartDirectionInstance(id_sd)
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=1)
        self.create_widgets()
        self.pack()

    def create_widgets(self):
        self.addBtn = tk.Button(self.root, text="Add building", fg="grey",
                              command=self.frameBuilding)

        self.addBtn.grid(column=1, row=0)

    def frameBuilding(self):
        pass