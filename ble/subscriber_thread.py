import collections
import socket
import threading
from concurrent.futures import thread
import time
from threading import Thread

from timeloop import Timeloop

import paho.mqtt.client as mqtt
from ble.log_thread import LogThread
from localization.localization import Status
from localization.localization_thread import LocalizationTimer
from map.elements.effector import Effectors
from map.elements.nodes import Nodes

import datetime

BROKER_IP = "test.mosquitto.org"    # "192.168.1.151" # my laptop

class MQTTSubscriber(LogThread):
    client: mqtt.Client
    devices_dict = {}   # dictionary of the form: {mac: {origin: <rssi_queue>}}, being mac = <device sniffed>, origin = <sniffer> (rberry pi)
    QUEUE_LENGTH = 5
    nodes: Nodes
    effectors: Effectors

    tl = Timeloop()

    map_device_mac = {} # dictionary of the form: {ID: [mac1, ..., macN]}

    def on_connect(self, client, userdata, flags, rc):
        self.client.subscribe("ble/rssi")
        self.client.subscribe("ble/activate")
        self.client.subscribe("ble/deactivate")
        self.client.message_callback_add('ble/rssi', self.on_rssi_received)
        self.client.message_callback_add('ble/activate', self.on_activate)
        self.client.message_callback_add('ble/deactivate', self.on_deactivate)

    def on_activate(self, client, userdata, msg):
        splits = str(msg.payload).split("$")    # TODO just need to know an ID
        mac = splits[0][2:-1]
        if len(splits) <= 1:
            # key is the mac
            key = mac
        else:
            # key is the device id
            device_id = splits[1]
            key = device_id

        if key not in self.devices_dict:
            self.devices_dict[key] = {}
        for origin in self.nodes.nodes:
            if origin.mac not in self.devices_dict[key]:
                self.devices_dict[key][origin.mac] = collections.deque(self.QUEUE_LENGTH * [{"timestamp": datetime.datetime.now(), "value": -100}], self.QUEUE_LENGTH)
        self.devices_dict[key]["status"] = Status.NAVIGATING

    def on_deactivate(self, client, userdata, msg):
        splits = str(msg.payload).split("$")
        mac = splits[0][2:-1]
        if len(splits) <= 1:
            # key is the mac
            key = mac
        else:
            # key is the device ID
            device_id = splits[1]
            key = device_id
        if key in self.devices_dict:
            self.devices_dict[key]["status"] = Status.INACTIVE


    @staticmethod
    def local_ip():
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)

    def on_rssi_received(self, client, userdata, msg):
        splits = str(msg.payload).split("$")
        if len(splits) >= 3:
            if len(splits) == 4:
                origin, mac, rssi, device_id = splits
                origin, mac = origin.lower()[2:], mac.lower()
                key = device_id.lower()
            else:
                origin, mac, rssi = splits
                origin, mac = origin.lower()[2:], mac.lower()
                key = mac
            # checking that it actually exists
            if key in self.devices_dict:
                # checking that node exists
                if origin in [node.mac.lower() for node in self.nodes.nodes]:
                    rssi = rssi[:-1]    # removing \n added by c++ code to have char*
                    # finally adding rssi
                    try:
                        rssi = int(rssi)
                        self.devices_dict[key][origin].append({"timestamp": datetime.datetime.now(), "value": rssi})
                    except:
                        self.errorLog("Unable to parse")
                else:
                    self.log("Unknown device communicating")
        else:
            self.errorLog("Unable to split")

    def on_message(self, client, userdata, msg):
        pass

    def run_timer(self):
        while True:
            localizationTimer = LocalizationTimer(self.client, self.nodes, self.effectors, self.devices_dict)
            localizationTimer.start()
            time.sleep(1)
            # TODO here it is the right place where to clean up a bit

    def __init__(self, name, nodes, effectors):
        LogThread.__init__(self, name)

        # Initializing mqtt protocol
        self.client = mqtt.Client()

        self.client.tls_set(ca_certs="../keys/mosquitto.org.crt", certfile="../keys/client.crt",
                       keyfile="../keys/client.key")

        self.client.connect(BROKER_IP, 8884, 60)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Initializing architecture stuff
        self.nodes, self.effectors = nodes, effectors

        # start timer executing localization thread
        t1 = threading.Thread(target=self.run_timer)
        t1.start()

    def run(self):
        self.client.loop_forever()

class TimerOfLocalization(LogThread):
    def __init__(self, subscriberThread: MQTTSubscriber):
        LogThread.__init__(self, "Prova")
        self.subscriberThread = subscriberThread

    def run(self):
        while True:
            localizationTimer = LocalizationTimer(
                self.subscriberThread.client,
                self.subscriberThread.nodes,
                self.subscriberThread.effectors,
                self.subscriberThread.devices_dict
            )
            localizationTimer.start()
            time.sleep(1)
