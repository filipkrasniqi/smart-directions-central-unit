import tkinter as tk

from map.ui.frame.add_building_frame import AddBuilding
from utils.parser import Parser

'''
UI associated with the list of buildings
'''
class Application(tk.Frame):
    def __init__(self, master, data_path):
        super().__init__(master)
        self.master, self.data_path = master, data_path
        self.buildings, self.buildingList, self.indexSelected, self.enable = self.getBuildings(), None, -1, True
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=1)
        self.create_widgets()
        self.showList()
        self.pack()

    '''
    Update the list with the buildings
    '''
    def showList(self):
        self.indexSelected = -1
        if self.buildingList is not None:
            self.buildingList.destroy()
            self.buildingList = None
        self.buildingList = tk.Listbox(self)
        for i, building in enumerate(self.buildings):
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
        return Parser(self.data_path).getInstance().read_buildings()

    '''
    Permanently save the buildings to file
    '''
    def saveBuildings(self):
        Parser(self.data_path).getInstance().write_buildings(self.buildings)

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

    '''
    Delete selected building
    '''
    def delete(self):
        self.buildings.pop(self.indexSelected)
        self.saveBuildings()
        self.showList()

    '''
    Open frame with selected building
    '''
    def frameEditBuilding(self):
        self.frameBuilding(self.buildings[self.indexSelected])

    '''
    Apply updates of buildings
    '''
    def save_persistent(self):
        self.saveBuildings()

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
        self.toggle(enable=False)
        if building is None:
            id = len(self.buildings)
        else:
            id = building.getId()
        newBuilding = AddBuilding(self, id, building)

    '''
    Reload building.
    Called when closing building frame
    '''
    def cancelUpdates(self):
        self.toggle(enable=True)
        self.buildings = self.getBuildings()
        self.showList()

    '''
    Apply new building.
    Called when closing building frame
    '''
    def addBuilding(self, newBuilding):
        self.toggle(enable=True)
        self.buildings.append(newBuilding)
        self.saveBuildings()
        self.showList()

    '''
    Apply update of the building.
    Called when closing building frame
    '''
    def editBuilding(self, newBuilding):
        self.toggle(enable=True)
        index = self.buildings.index(newBuilding)
        self.buildings[index] = newBuilding
        self.saveBuildings()
        self.showList()