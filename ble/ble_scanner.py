import time

from beacontools import BeaconScanner

from ble.log_thread import LogThread


class ScanThread(LogThread):
    scanner: BeaconScanner
    def __init__(self, name, scanner):
        LogThread.__init__(self, name)
        self.name = name
        self.scanner = scanner

    def run(self):
        self.log("START SCAN")
        self.scanner.start()
        time.sleep(600)
        self.log("END SCAN")
        self.scanner.stop()