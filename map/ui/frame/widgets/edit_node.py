import tkinter as tk

from map.elements.node import Node

'''
UI associated to the updated of an anchor
'''
class EditNode(tk.Toplevel):
    def __init__(self, master, node):
        tk.Toplevel.__init__(self, master=master)
        self.wm_title("Edit {}".format("anchor" if isinstance(node, Node) else "effector"))
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.wm_geometry("+%d+%d" % (node.getCoordinates()[0] + 20, node.getCoordinates()[1] + 57))

        self.node = node

        self.name = tk.Entry(self)
        self.name.grid(column=0, row=0)

        self.mac = tk.Entry(self)
        self.mac.grid(column=0, row=1)

        self.cancel = tk.Button(self, text="Go back", command=self.goBack)
        self.cancel.grid(column=0, row=2)

        self.save = tk.Button(self, text="Save", command=self.save)
        self.save.grid(column=0, row=3)

        self.__initUI()

    def __initUI(self):
        self.name.insert(0, self.node.name)
        self.mac.insert(0, self.node.mac)

    def on_closing(self):
        self.destroy()

    def save(self):
        self.node.mac, self.node.name = self.mac.get(), self.name.get()
        self.destroy()

    def goBack(self):
        self.destroy()