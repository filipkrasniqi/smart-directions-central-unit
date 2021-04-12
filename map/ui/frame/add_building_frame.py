import tkinter as tk
from tkinter import filedialog

from map.elements.planimetry.building import Building
from map.elements.planimetry.point_type import PointType
from map.ui.frame.widgets.edit_node import EditNode
from map.ui.frame.widgets.edit_effector import EditEffector
from map.ui.frame.widgets.edit_poi import EditPoI
from map.ui.frame.widgets.tooltip import ToolTip
from utils.parser import Parser
from PIL import ImageTk, Image

import numpy as np

'''
UI associated with adding/updating a building
'''
# TODO rimuovere possibilità di aprire due UI contemporaneamente
class AddBuilding(tk.Toplevel):
    def __init__(self, master, id, building = None):
        tk.Toplevel.__init__(self, master=master)
        self.wm_geometry("1980x1024")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.isUpdate = building is not None

        self.currentBuilding, self.selectedObject, self.tipWindow, self.id, self.currentFloor, \
        self.editNodeWindow, self.editPoIWindow, self.editEffectorWindow = building, None, None, id, 0, None, None, None

        self.wm_title("New building" if not self.isUpdate else "Edit building {}".format(self.currentBuilding))

        # setting grid shape
        self.master.grid_columnconfigure(0, weight=6)
        self.master.grid_columnconfigure(1, weight=1)

        self.canvas = None

        # adding frames
        self.loadBtn = tk.Button(self, text="Load from file", fg="grey",
                             command=self.loadFromFile)
        self.loadBtn.grid(column=1, row=0)

        self.nameEntry = tk.Entry(self)
        self.nameEntry.grid(column=1, row=1)
        self.nameEntry.configure(state="disabled")

        self.anchorBtn = tk.Button(self, text="Add anchor", fg="grey",
                             command=self.addAnchor)
        self.anchorBtn.grid(column=1, row=2)
        self.anchorBtn.configure(state="disabled")

        self.effectorBtn = tk.Button(self, text="Add effector", fg="grey",
                             command=self.addEffector)
        self.effectorBtn.grid(column=1, row=3)
        self.effectorBtn.configure(state="disabled")

        self.poiBtn = tk.Button(self, text="Add PoI", fg="grey",
                             command=self.addPoI)
        self.poiBtn.grid(column=1, row=4)
        self.poiBtn.configure(state="disabled")

        self.cancelUpdates = tk.Button(self, text="Delete selected", fg="grey",
                                     command=self.deleteSelected)
        self.cancelUpdates.grid(column=1, row=5)

        self.saveBtn = tk.Button(self, text="Save and go back", fg="grey",
                                     command=self.save)
        self.saveBtn.grid(column=1, row=6)
        self.saveBtn.configure(state="disabled")

        self.cancelUpdates = tk.Button(self, text="Cancel updates", fg="grey",
                                     command=self.cancel)
        self.cancelUpdates.grid(column=1, row=7)

        self.floorEntry = tk.Entry(self)
        self.floorEntry.grid(column=1, row=8)
        self.floorEntry.configure(state="disabled")

        self.confirmFloor = tk.Button(self, text="Change floor", fg="grey",
                                     command=self.changeFloor)
        self.confirmFloor.grid(column=1, row=9)
        self.confirmFloor.configure(state="disabled")

        self.loadBtn = tk.Button(self, text="Load home", fg="grey",
                             command=self.buildHome)
        self.loadBtn.grid(column=1, row=10)

        if self.isUpdate:
            self.enableButtons()
            self.updateUIWithBuildingInfo()
            self.drawFloor()

        self.grid()

    '''
    Listener on frame being closed. Not handling asking for confirmation.
    '''
    def on_closing(self):
        self.master.toggle(enable=True)
        self.master.reset_selected()
        self.building = None
        self.destroy()

    def buildHome(self):
        self.set_building(Building(id=self.id, name="Casa - {}".format(self.id)))
        self.currentFloor = 0
        self.enableButtons()
        self.updateUIWithBuildingInfo()
        self.drawFloor()

    '''
    Listener on loading building from file.
    Opens UI to select files. Updates the UI if a proper file is provided with the new building.
    '''
    def loadFromFile(self):
        filename = filedialog.askopenfilename(initialdir = "/",title = "Select file",filetypes = [("Txt files", ".txt")])
        parser = Parser("").getInstance()
        points = parser.read_points_from_txt(filename)
        self.set_building(Building(id=self.id, latitude=0, longitude=0, points=points, name="Nuovo edificio - {}".format(self.id)))
        self.currentFloor = 0
        self.enableButtons()
        self.updateUIWithBuildingInfo()
        self.drawFloor()

    def set_building(self, building):
        self.currentBuilding = building
        #self.nameEntry.insert(0, "{} - {}".format(self.currentBuilding.name, self.currentBuilding.id))
    '''
    Updates the UI with the building information (name and floor)
    '''
    def updateUIWithBuildingInfo(self):
        self.floorEntry.insert(0, str(self.currentFloor))
        self.nameEntry.insert(0,self.currentBuilding.name)
        self.grid()

    '''
    Listener to change floor btn. If the floor is valid, it updates the UI with the new floor.
    '''
    def changeFloor(self):
        try:
            currentFloor = int(self.floorEntry.get())
            if currentFloor < self.currentBuilding.getNumberFloors():
                self.currentFloor = currentFloor
                self.drawFloor()
        except:
            pass

    '''
    Draw a canvas with the current floor of the building
    '''
    def drawFloor(self):
        if self.currentBuilding is not None:
            matrixToDraw = self.currentBuilding.getFloor(self.currentFloor)
            connectionsToDraw = self.currentBuilding.getConnectionsMatrix(self.currentFloor)

            # building matrix depending on the cell value
            matrixRGB = np.zeros((matrixToDraw.shape[1], matrixToDraw.shape[0], 3), dtype=np.uint8)
            for i, row in enumerate(matrixToDraw):
                for j, cell in enumerate(row):
                    if self.selectedObject is not None and i == self.selectedObject[0] and j == self.selectedObject[1]:
                        objectType = self.currentBuilding.getObjectTypeAt(i, j, self.currentFloor)
                        if PointType.isObject(objectType):
                            currentObject = self.currentBuilding.getObjectAt(self.currentFloor, (i, j))
                            matrixRGB[j, i] = currentObject.getSelectedColor()
                        else:
                            matrixRGB[j, i] = [255, 0, 255]
                    else:
                        if not self.currentBuilding.isOccupied(i, j, self.currentFloor):
                            matrixRGB[j, i] = [255, 128, 0] if cell == PointType.INDOOR else [0,191,255] if cell == PointType.OUTDOOR else [128,128,128]
                        else:
                            currentObject = self.currentBuilding.getObjectAt(self.currentFloor, (i, j))
                            matrixRGB[j, i] = currentObject.getColor()

            for i, row in enumerate(connectionsToDraw):
                for j, cell in enumerate(row):
                    if PointType.isValid(cell):
                        matrixRGB[j, i] = [255, 255, 255] if cell == PointType.STAIR else ([0, 0, 0] if cell == PointType.LIFT else ([255, 0, 255] if cell == PointType.STAIR_PIVOT else [128, 0, 255]))
            # resizing the matrix for the canvas and adjusting the canvas
            self.hsize = 400
            self.ratioUIMatrix = (self.hsize / float(matrixRGB.shape[0]))
            self.finalWidth = int((float(matrixRGB.shape[1]) * float(self.ratioUIMatrix)))

            if self.canvas is not None:
                self.canvas.destroy()

            self.canvas = tk.Canvas(self, width=self.finalWidth, height=self.hsize)
            self.canvas.grid(column=0, row=0, rowspan=8)
            # building the image and resizing it
            image = Image.fromarray(matrixRGB, 'RGB')
            self.matrix = matrixRGB
            image = image.resize((self.finalWidth,self.hsize), Image.AFFINE)
            photo = ImageTk.PhotoImage(image=image)
            self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
            # creating the grid in the canvas
            row, col = int(self.ratioUIMatrix), int(self.ratioUIMatrix)
            while row < self.hsize or col < self.finalWidth:
                if row < self.hsize:
                    self.canvas.create_line(0, row, self.finalWidth, row)
                    row = int(row+self.ratioUIMatrix)
                if col < self.finalWidth:
                    self.canvas.create_line(col, 0, col, self.hsize)
                    col = int(col+self.ratioUIMatrix)
            self.canvas.bind('<Button-1>', self.onCanvasClick)
            self.canvas.bind('<Button-2>', self.onCanvasDoubleClick)
            self.canvas.bind('<Motion>', self.onCanvasHover)

            self.canvas.mainloop()

    '''
    Shows tip on hover on objects
    '''
    def showTipWindow(self, id, text, x1, y1):
        self.clearTipWindow()
        self.tipWindow = ToolTip(self, id, text, x1, y1)

    '''
    Removes the tip on hover out
    '''
    def clearTipWindow(self):
        if self.tipWindow is not None:
            self.tipWindow.destroy()
            self.tipWindow = None

    '''
    Listener on hover on canvas: given x and y, it retrieves the canvas and matrix coordinates, and 
    it checks if the cell is associated with an object. If so, it shows a tip with the information.
    '''
    def onCanvasHover(self, event):
        x, y = self.transformClickCoordinatesToCanvas(event.x, event.y)
        xMatrix, yMatrix = self.transformCanvasCoordinatesToMatrix(x, y)
        objectType = self.currentBuilding.getObjectTypeAt(xMatrix, yMatrix, self.currentFloor)
        shownTip = False

        # show for selected
        if PointType.isValid(objectType) and PointType.isObject(objectType):
            shownTip = True
            currentObj = self.currentBuilding.getObjectAt(self.currentFloor, (xMatrix, yMatrix))
            if self.tipWindow is None or self.tipWindow != currentObj.getId():
                self.showTipWindow(currentObj.__hash__(), currentObj, x, y)
        else:
            self.clearTipWindow()

        # show for other cases
        if not shownTip:
            objectType = self.currentBuilding.getConnectionTypeAt(xMatrix, yMatrix, self.currentFloor)
            if PointType.isConnection(objectType):
                currentObj = self.currentBuilding.getConnectionAt(xMatrix, yMatrix, self.currentFloor)
                if currentObj.pivot != None:
                    currentObj = currentObj.pivot
                    if self.tipWindow is None or self.tipWindow != currentObj.__hash__():
                        self.showTipWindow(currentObj.__hash__(), currentObj, x, y)
    '''
    Clears all the opened windows
    '''
    def clearAllWindows(self):
        self.clearTipWindow()
        self.clearEditNodeWindow()
        self.clearEditEffectorWindow()
        self.clearEditPoIWindow()

    def reset_selected(self):
        self.indexSelected = -1
        self.enableSelected(False)

    '''
    Eventually clears the edit node window
    '''
    def clearEditNodeWindow(self):
        if self.editNodeWindow is not None:
            self.editNodeWindow.destroy()
            self.editNodeWindow = None

    '''
    Shows the edit node window
    '''
    def showEditNodeWindow(self, node):
        self.clearAllWindows()
        self.editNodeWindow = EditNode(self, node)

    '''
    Eventually clears the edit effector window
    '''
    def clearEditEffectorWindow(self):
        if self.editEffectorWindow is not None:
            self.editEffectorWindow.destroy()
            self.editEffectorWindow = None

    '''
    Shows the edit effector window
    '''
    def showEditEffectorWindow(self, effector):
        self.clearAllWindows()
        self.editEffectorWindow = EditEffector(self, effector)

    '''
    Eventually clears the edit PoI window
    '''
    def clearEditPoIWindow(self):
        if self.editPoIWindow is not None:
            self.editPoIWindow.destroy()
            self.editPoIWindow = None

    '''
    Shows the edit PoI window
    '''
    def showEditPoIWindow(self, poi):
        self.clearAllWindows()
        self.editPoIWindow = EditPoI(self, poi)

    '''
    Listener to double click event on the canvas.
    Given x and y, it retrieves the matrix coordinates.
    If x,y are associated to an object, it shows the related update frame.
    '''
    def onCanvasDoubleClick(self, event):
        x, y = self.transformClickCoordinatesToCanvas(event.x, event.y)
        x, y = self.transformCanvasCoordinatesToMatrix(x, y)
        objectType = self.currentBuilding.getObjectTypeAt(x, y, self.currentFloor)

        if PointType.isValid(objectType) and PointType.isObject(objectType):
            self.selectedObject = None
            objToEdit = self.currentBuilding.getObjectAt(self.currentFloor, (x, y))
            # open corresponding modal: effector, node, poi
            if objectType == PointType.ANCHOR:
                self.showEditNodeWindow(objToEdit)
            elif objectType == PointType.EFFECTOR:
                self.showEditEffectorWindow(objToEdit)
            else:
                self.showEditPoIWindow(objToEdit)

    '''
    Transformation to get the coordinates in the canvas system
    It seems the coordinates are shifted by 2
    '''
    def transformClickCoordinatesToCanvas(self, x, y):
        return x-2, y-2

    '''
    Normalize values in the range of indices of matrix
    '''
    def transformCanvasCoordinatesToMatrix(self, x, y):
        return int(x/self.ratioUIMatrix), int(y/self.ratioUIMatrix)

    '''
    Handling event of clicking in the canvas
    First click (i.e., selectedObject is null): if coordinates correspond to an object, select it
    Second click: if coordinates correspond to an object, select it; if to a walkable, move it
    '''
    def onCanvasClick(self, event):
        x, y = self.transformClickCoordinatesToCanvas(event.x, event.y)
        x, y = self.transformCanvasCoordinatesToMatrix(x, y)
        objectType = self.currentBuilding.getObjectTypeAt(x, y, self.currentFloor)

        if PointType.isValid(objectType):
            if PointType.isObject(objectType):
                self.selectedObject = (x, y)
            else:
                if self.selectedObject is not None:
                    if PointType.isObject(objectType):
                        self.selectedObject = (x, y)
                    else:
                        self.currentBuilding.changeObjectPosition(self.currentFloor, self.selectedObject, (x, y))
                        self.selectedObject = None
            self.drawFloor()
        else:
            self.selectedObject = None

    '''
    Enable all buttons
    '''
    def enableButtons(self):
        for child in self.winfo_children():
            child.configure(state="normal")

    '''
    Add the anchor to the building at the first available position and updates UI
    '''
    def addAnchor(self):
        self.currentBuilding.addAnchor(self.currentFloor)
        self.drawFloor()

    '''
    Add the effector to the building at the first available position and updates UI
    '''
    def addEffector(self):
        self.currentBuilding.addEffector(self.currentFloor)
        self.drawFloor()

    '''
    If present, it deletes the selected object
    '''
    def deleteSelected(self):
        if self.selectedObject is not None:
            i, j = self.selectedObject
            objectType = self.currentBuilding.getObjectTypeAt(i, j, self.currentFloor)
            if PointType.isObject(objectType):
                self.selectedObject = None
                self.currentBuilding.deleteObject(i, j, self.currentFloor)
                self.drawFloor()

    '''
    Add the PoI to the building at the first available position and updates UI
    '''
    def addPoI(self):
        self.currentBuilding.addPoI(self.currentFloor)
        self.drawFloor()

    '''
    Saves the current building and closes the window
    '''
    def save(self):
        self.currentBuilding.name = self.nameEntry.get()
        if self.isUpdate:
            self.master.edit_building(self.currentBuilding)
        else:
            self.master.add_building(self.currentBuilding)
        self.destroy()

    '''
    All updates are canceled, and the window gets closed
    '''
    def cancel(self):
        self.master.cancelUpdates()
        self.destroy()
