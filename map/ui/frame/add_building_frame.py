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

        self.saveBtn = tk.Button(self, text="Save and go back", fg="grey",
                                     command=self.save)
        self.saveBtn.grid(column=1, row=5)
        self.saveBtn.configure(state="disabled")

        self.cancelUpdates = tk.Button(self, text="Cancel updates", fg="grey",
                                     command=self.cancel)
        self.cancelUpdates.grid(column=1, row=6)

        self.floorEntry = tk.Entry(self)
        self.floorEntry.grid(column=1, row=7)
        self.floorEntry.configure(state="disabled")

        self.confirmFloor = tk.Button(self, text="Change floor", fg="grey",
                                     command=self.changeFloor)
        self.confirmFloor.grid(column=1, row=8)
        self.confirmFloor.configure(state="disabled")

        if self.isUpdate:
            self.enableButtons()
            self.updateUIWithBuildingInfo()
            self.drawFloor()

    '''
    Listener on frame being closed. Not handling asking for confirmation.
    '''
    def on_closing(self):
        self.master.toggle(enable=True)
        self.destroy()

    '''
    Listener on loading building from file.
    Opens UI to select files. Updates the UI if a proper file is provided with the new building.
    '''
    def loadFromFile(self):
        filename = filedialog.askopenfilename(initialdir = "/",title = "Select file",filetypes = [("Txt files", ".txt")])
        parser = Parser("").getInstance()
        points = parser.read_points_from_txt(filename)
        self.currentBuilding = Building(self.id, 0, 0, points, "Nuovo edificio")
        self.currentFloor = 0
        self.updateUIWithBuildingInfo()
        self.enableButtons()
        self.drawFloor()

    '''
    Updates the UI with the building information (name and floor)
    '''
    def updateUIWithBuildingInfo(self):
        self.floorEntry.insert(0, str(self.currentFloor))
        self.nameEntry.insert(0, self.currentBuilding.name)

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
            # TODO da cambiare quando ho immagini corrette ma è utile ora
            matrixToDraw = matrixToDraw[:int(matrixToDraw.shape[0]/2), :int(matrixToDraw.shape[1]/2)]

            # building matrix depending on the cell value
            matrixRGB = np.zeros((matrixToDraw.shape[0], matrixToDraw.shape[1], 3), dtype=np.uint8)
            for i, row in enumerate(matrixToDraw):
                for j, cell in enumerate(row):
                    if self.selectedObject is not None and i == self.selectedObject[0] and j == self.selectedObject[1]:
                        currentSelectedObject = self.currentBuilding.getObjectTypeAt(self.currentFloor, i, j)
                        if PointType.isObject(currentSelectedObject):
                            currentObject = self.currentBuilding.getObjectAt(self.currentFloor, (i, j))
                            matrixRGB[i, j] = currentObject.getSelectedColor()
                        else:
                            matrixRGB[i, j] = [255, 0, 255]
                    else:
                        if not self.currentBuilding.isOccupied(i, j, self.currentFloor):
                            matrixRGB[i,j] = [255, 128, 0] if cell == PointType.INDOOR else [0,191,255] if cell == PointType.OUTDOOR else [128,128,128]
                        else:
                            currentObject = self.currentBuilding.getObjectAt(self.currentFloor, (i, j))
                            matrixRGB[i, j] = currentObject.getColor()

            # resizing the matrix for the canvas and adjusting the canvas
            finalWidth = 1200
            self.ratioUIMatrix = (finalWidth / float(matrixRGB.shape[1]))
            self.hsize = int((float(matrixRGB.shape[0]) * float(self.ratioUIMatrix)))
            self.canvas = tk.Canvas(self, width=finalWidth, height=self.hsize)
            self.canvas.grid(column=0, row=0, rowspan=8)
            # building the image and resizing it
            image = Image.fromarray(matrixRGB, 'RGB')
            self.matrix = matrixRGB
            image = image.resize((finalWidth,self.hsize), Image.AFFINE)
            photo = ImageTk.PhotoImage(image=image)
            self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
            # creating the grid in the canvas
            row, col = int(self.ratioUIMatrix), int(self.ratioUIMatrix)
            while row < self.hsize or col < finalWidth:
                if row < self.hsize:
                    self.canvas.create_line(0, row, finalWidth, row)
                    row = int(row+self.ratioUIMatrix)
                if col < finalWidth:
                    self.canvas.create_line(col, 0, col, self.hsize)
                    col = int(col+self.ratioUIMatrix)
            self.canvas.bind('<Button-1>', self.onCanvasClick)
            self.canvas.bind('<Double-1>', self.onCanvasDoubleClick)
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
        currentSelectedObject = self.currentBuilding.getObjectTypeAt(self.currentFloor, yMatrix, xMatrix)

        if PointType.isValid(currentSelectedObject) and PointType.isObject(currentSelectedObject):
            currentObj = self.currentBuilding.getObjectAt(self.currentFloor, (yMatrix, xMatrix))
            if self.tipWindow is None or self.tipWindow != currentObj.getId():
                self.showTipWindow(currentObj.getId(), currentObj, x, y)
        else:
            self.clearTipWindow()

    '''
    Clears all the opened windows
    '''
    def clearAllWindows(self):
        self.clearTipWindow()
        self.clearEditNodeWindow()
        self.clearEditEffectorWindow()
        self.clearEditPoIWindow()

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
        currentSelectedObject = self.currentBuilding.getObjectTypeAt(self.currentFloor, y, x)

        if PointType.isValid(currentSelectedObject) and PointType.isObject(currentSelectedObject):
            self.selectedObject = None
            objToEdit = self.currentBuilding.getObjectAt(self.currentFloor, (y, x))
            # open corresponding modal: effector, node, poi
            if currentSelectedObject == PointType.ANCHOR:
                self.showEditNodeWindow(objToEdit)
            elif currentSelectedObject == PointType.EFFECTOR:
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
        currentSelectedObject = self.currentBuilding.getObjectTypeAt(self.currentFloor, y, x)

        if PointType.isValid(currentSelectedObject):
            if PointType.isObject(currentSelectedObject):
                self.selectedObject = (y, x)
            else:
                if self.selectedObject is not None:
                    if PointType.isObject(currentSelectedObject):
                        self.selectedObject = (y, x)
                    else:
                        self.currentBuilding.changeObjectPosition(self.currentFloor, self.selectedObject, (y, x))
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
            self.master.editBuilding(self.currentBuilding)
        else:
            self.master.addBuilding(self.currentBuilding)
        self.destroy()

    '''
    All updates are canceled, and the window gets closed
    '''
    def cancel(self):
        self.master.cancelUpdates()
        self.destroy()
