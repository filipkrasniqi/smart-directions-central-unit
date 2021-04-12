import tkinter as tk

import map.elements.planimetry.sd_instance as sd_instance_class #import SmartDirectionInstance, SmartDirectionWrapperInstance
from map.ui.frame.add_building_frame import AddBuilding
from utils.parser import Parser

'''
UI associated with the list of buildings
'''
class BuildingListFrame(tk.Toplevel):
    def __init__(self, master, id_sd, current_sd = None):
        tk.Toplevel.__init__(self, master=master)
        self.master = master
        self.isUpdate = True
        if current_sd is None:
            self.isUpdate = False
            self.sd_instance = sd_instance_class.SmartDirectionInstance(id_sd, [])
        else:
            self.sd_instance = self.getInstanceFromFile(current_sd)
        self.buildingList, self.indexSelected, self.enable = None, -1, True
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=1)
        self.create_widgets()
        self.showList()
        self.grid()

    '''
    Update the list with the buildings
    '''
    def showList(self):
        if self.buildingList is None:
            self.buildingList = tk.Listbox(self)
        else:
            self.buildingList.delete(0, tk.END)
        for i, building in enumerate(self.sd_instance.buildings):
            self.buildingList.insert(i, building)
        self.buildingList.grid(column=0, row=1)
        self.buildingList.bind("<<ListboxSelect>>", self.onBuildingSelected)

    '''
    Listener for selection of building
    '''
    def onBuildingSelected(self, event):
        selection = event.widget.curselection()
        if selection:
            self.indexSelected = selection[0]
        else:
            self.indexSelected = -1
        self.enableSelected(self.indexSelected >= 0)

    '''
    Activate UI for edit (to be called when a building is selected)
    '''
    def enableSelected(self, enable):
        state = "normal" if enable else "disabled"
        self.editBtn.configure(state=state)
        self.deleteBtn.configure(state=state)

    '''
    Read last save of buildings
    '''
    def getBuildings(self):
        return self.sd_instance.buildings

    def getInstanceFromFile(self, sd_wrapper: sd_instance_class.SmartDirectionWrapperInstance):
        return Parser().getInstance().read_sd_buildings(sd_wrapper)

    '''
    Permanently save the buildings to file
    '''
    def saveBuildings(self, close_window = False):
        self.sd_instance.name = self.nameEntry.get()
        Parser().getInstance().write_sd_buildings(self.sd_instance)
        if close_window:

            if self.isUpdate:
                self.master.edit_sd_instance(self.sd_instance)
            else:
                self.master.add_sd_instance(self.sd_instance)

            self.sd_instance = None
            self.destroy()

    '''
    Add all UI widgets
    '''
    def create_widgets(self):
        self.addBtn = tk.Button(self, text="Add building", fg="grey",
                              command=self.frameBuilding)

        self.addBtn.grid(column=1, row=0)
        self.confirmBtn = tk.Button(self, text="Save", fg="grey",
                              command=self.save_persistent)

        self.confirmBtn.grid(column=1, row=1)

        self.editBtn = tk.Button(self, text="Edit", fg="grey",
                              command=self.frameEditBuilding)

        self.editBtn.grid(column=1, row=2)

        self.deleteBtn = tk.Button(self, text="Delete", fg="grey",
                              command=self.delete)

        self.deleteBtn.grid(column=1, row=3)
        self.enableSelected(False)

        self.nameEntry = tk.Entry(self)
        self.nameEntry.grid(column=1, row=4)
        self.nameEntry.insert(0, self.sd_instance.name)

    '''
    Delete selected building
    '''
    def delete(self):
        self.sd_instance.buildings.pop(self.indexSelected)
        self.reset_selected()
        self.saveBuildings()
        self.showList()

    def reset_selected(self):
        self.indexSelected = -1
        self.enableSelected(False)

    '''
    Open frame with selected building
    '''
    def frameEditBuilding(self):
        self.frameBuilding(self.sd_instance.buildings[self.indexSelected])

    '''
    Apply updates of buildings
    '''
    def save_persistent(self):
        self.saveBuildings(close_window=True)

    '''
    Enable / disable UI
    '''
    def toggle(self, enable = None):
        if enable is not None:
            self.enable = enable
        else:
            self.enable = not self.enable
        for child in self.winfo_children():
            if child.widgetName != 'toplevel':
                child.configure(state="normal" if self.enable else "disabled")

    '''
    Open building frame, both for update or add
    '''
    def frameBuilding(self, building = None):
        self.reset_selected()
        if building is None:
            if len(self.sd_instance.buildings) <= 0:
                id = 1
            else:
                id = max([b.id for b in self.sd_instance.buildings])+1
        else:
            id = building.getId()
        newBuilding = AddBuilding(self, id, building)

    '''
    Reload building.
    Called when closing building frame
    '''
    def cancelUpdates(self):
        self.reset_selected()
        self.showList()

    '''
    Apply new building.
    Called when closing building frame
    '''
    def add_building(self, newBuilding):
        self.reset_selected()
        self.sd_instance.buildings.append(newBuilding)
        self.saveBuildings()
        self.showList()

    '''
    Apply update of the building.
    Called when closing building frame
    '''
    def edit_building(self, newBuilding):
        self.reset_selected()
        index = self.sd_instance.buildings.index(newBuilding)
        self.sd_instance.buildings[index] = newBuilding
        self.saveBuildings()
        self.showList()