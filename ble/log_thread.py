import threading
import time


class LogThread(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def log(self, msg):
        print("{} @ {}: {}".format(self.name, time.ctime(time.time()).split(" ")[3], msg))
    def errorLog(self, err):
        print("ERROR: {} @ {}: {}".format(self.name, time.ctime(time.time()).split(" ")[3], err))