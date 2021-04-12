import tkinter as tk

from map.ui.frame.building_list_frame import BuildingListFrame
from map.ui.frame.sd_list_frame import SDListFrame
from utils.parser import Parser

if __name__ == '__main__':
    data_path = "/Users/filipkrasniqi/PycharmProjects/smartdirections/assets/smart_directions/"
    root = tk.Tk()
    _ = Parser(data_path).getInstance()
    app = SDListFrame(master=root, data_path=data_path)
    app.mainloop()