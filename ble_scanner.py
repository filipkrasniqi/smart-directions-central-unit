import functools
import threading
import time

from pubsub import pub
# import pynput
# from pynput.keyboard import Listener

from beacontools import BeaconScanner, BluetoothAddressType

from ble.ble_scanner import ScanThread
from ble.detectors import proximity_callback, communicate_callback
from ble.publisher import MQTTPublisher
from ble.subscriber_thread import MQTTSubscriber


class BLEScanner:
    scannerThread: ScanThread
    communicate: bool

    def __init__(self, init=True, communicate = True):
        self.communicate = communicate
        if(init):
            self.init()
            # self.init_keyboard_listener()

    def init_keyboard_listener(self):
        # with Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            # listener.join()
        pass

    def start_scan(self):
        self.scannerThread = ScanThread("BLEScanner", self.scanner)
        self.scannerThread.start()

    # def scan_thread():
    def init(self):
        if not self.communicate:
            scanner_callback = proximity_callback
        else:
            publisher = MQTTPublisher()
            scanner_callback = functools.partial(communicate_callback, publisher)

        self.scanner = BeaconScanner(
            scanner_callback,
            scan_parameters={"address_type": BluetoothAddressType.PUBLIC}
        )

        self.start_scan()

    def on_press(self, key):
        print(key)

    def on_release(self, key):
        # print(key)
        pass