import tkinter as tk

from map.ui.frame.add_building_frame import AddBuilding
from map.ui.frame.building_list_frame import BuildingListFrame
from map.ui.frame.test_grid import TestGrid
from utils.parser import Parser

'''
UI associated with the list of SmartDirection instances
'''
class SDListFrame(tk.Frame):
    def __init__(self, master, data_path):
        super().__init__(master)
        self.master, self.data_path = master, data_path
        self.sd_instances, self.sd_list, self.indexSelected, self.enable = self.getSDInstances(), None, -1, True
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=1)
        self.create_widgets()
        self.showList()
        self.grid()

    '''
    Update the list with the SmartDirection instances
    '''
    def showList(self):
        self.indexSelected = -1
        if self.sd_list is not None:
            self.sd_list.destroy()
            self.sd_list = None
        self.sd_list = tk.Listbox(self)
        for i, sdInstance in enumerate(self.sd_instances):
            self.sd_list.insert(i, "{} - {}".format(sdInstance.name, sdInstance.id))
        self.sd_list.grid(column=0, row=0)
        self.sd_list.bind("<<ListboxSelect>>", self.on_sd_selected)

    '''
    Listener for selection of SmartDirection instance
    '''
    def on_sd_selected(self, event):
        selection = event.widget.curselection()
        if selection:
            self.indexSelected = selection[0]
        else:
            self.indexSelected = -1
        self.enableSelected(self.indexSelected >= 0)

    '''
    Activate UI for edit (to be called when a SmartDirection instance is selected)
    '''
    def enableSelected(self, enable):
        state = "normal" if enable else "disabled"
        self.editBtn.configure(state=state)
        self.deleteBtn.configure(state=state)

    '''
    Read last save of SmartDirection instances
    '''
    def getSDInstances(self):
        return Parser().getInstance().read_smartdirections_instances()

    '''
    Permanently save the SmartDirection instances to file
    '''
    def saveSDInstances(self):
        Parser().getInstance().write_sd_instances(self.sd_instances)

    '''
    Add all UI widgets
    '''
    def create_widgets(self):
        self.addBtn = tk.Button(self.master, text="Add SD instance", fg="grey",
                                command=self.frame_building_list)
        self.addBtn.grid(column=1, row=0, sticky='nsew')

        self.editBtn = tk.Button(self.master, text="Edit", fg="grey",
                                 command=self.frame_edit_sd_instance)
        self.editBtn.grid(column=1, row=1, sticky='nsew')

        self.deleteBtn = tk.Button(self.master, text="Delete", fg="grey",
                              command=self.delete)
        self.deleteBtn.grid(column=1, row=2, sticky='nsew')

        self.enableSelected(False)

    '''
    Delete selected SmartDirection instance
    '''
    def delete(self):
        to_delete = self.sd_instances.pop(self.indexSelected)
        Parser().getInstance().clear_sd(to_delete)
        self.saveSDInstances()
        self.showList()

    '''
    Open frame with selected SmartDirection instance
    '''
    def frame_edit_sd_instance(self):
        self.frame_building_list(self.sd_instances[self.indexSelected])

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
                pass#child.configure(state="normal" if self.enable else "disabled")

    '''
    Open SmartDirection instance frame, both for update or add
    '''
    def frame_building_list(self, sd_instance = None):
        self.toggle(enable=False)
        if sd_instance is None:
            try:
                id = max([s.id for s in self.sd_instances])+1
            except:
                id = 0
        else:
            id = sd_instance.id
        newSDInstance = BuildingListFrame(self, id, sd_instance)

    '''
    Reload SmartDirection instance.
    Called when closing SmartDirection instance frame
    '''
    def cancelUpdates(self):
        self.toggle(enable=True)
        self.sd_instances = self.getSDInstances()
        self.showList()

    '''
    Apply new SmartDirection instance.
    Called when closing SmartDirection instance frame
    '''
    def add_sd_instance(self, sd_instance):
        self.toggle(enable=True)
        self.sd_instances.append(sd_instance.getWrapper())
        self.saveSDInstances()
        self.showList()

    '''
    Apply update of the SmartDirection instance.
    Called when closing SmartDirection instance frame
    '''
    def edit_sd_instance(self, updated_sd_instance):
        self.toggle(enable=True)
        index = self.sd_instances.index(updated_sd_instance)
        self.sd_instances[index] = updated_sd_instance.getWrapper()
        self.saveSDInstances()
        self.showList()