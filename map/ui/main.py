import tkinter as tk

from map.ui.frame.application import Application
from utils.parser import Parser

if __name__ == '__main__':
    data_path = "/Users/filipkrasniqi/PycharmProjects/smartdirections/assets/"
    root = tk.Tk()
    app = Application(master=root, data_path=data_path)
    app.mainloop()