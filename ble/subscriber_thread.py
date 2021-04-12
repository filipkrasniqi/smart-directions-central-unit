import collections
import socket
import threading
from concurrent.futures import thread
import time
from threading import Thread

import paho.mqtt.client as mqtt
from ble.log_thread import LogThread
from localization.localization import Status, LocalizationType
from localization.localization_thread import LocalizationTimer
from map.elements.effector import Effectors
from map.elements.nodes import Nodes

import datetime

from utils.parser import Parser

BROKER_IP = "80.211.69.17"    # "192.168.1.151" # my laptop

# TODO associarlo ad una SD instance, non ad un building
class MQTTSubscriber(LogThread):
    client: mqtt.Client
    devices_dict = {}   # dictionary of the form: {mac: {origin: <rssi_queue>}}, being mac = <device sniffed>, origin = <sniffer> (rberry pi)
    QUEUE_LENGTH = 5
    nodes: Nodes
    effectors: Effectors
    all_devs = set()
    log_nodes_dict = {} # for log purposes: shows last communication timestamp for each node

    def on_connect(self, client, userdata, flags, rc):
        self.client.subscribe("directions/anchor/proximity/#")
        self.client.subscribe("directions/device/activate/#")
        self.client.subscribe("directions/device/deactivate/#")
        self.client.message_callback_add('directions/anchor/proximity/#', self.on_rssi_received)
        self.client.message_callback_add('directions/device/activate/#', self.on_activate)
        self.client.message_callback_add('directions/device/deactivate/#', self.on_deactivate)

    def on_activate(self, client, userdata, msg):
        key = msg.topic.split("/")[-1].lower()
        self.activate_device(key)

    def activate_device(self, key):
        if key not in self.devices_dict:
            self.devices_dict[key] = {}
        for origin in self.anchors():
            if origin.mac not in self.devices_dict[key]:
                self.devices_dict[key][origin.mac] = collections.deque(self.QUEUE_LENGTH * [{"timestamp": datetime.datetime.now(), "value": -100}], self.QUEUE_LENGTH)
        self.devices_dict[key]["status"] = Status.NAVIGATING

    def on_deactivate(self, client, userdata, msg):
        key = msg.topic.split("/")[-1].lower()
        if key in self.devices_dict:
            self.devices_dict[key]["status"] = Status.INACTIVE

    def anchors(self):
        return self.sd_instance.rawAnchors()

    def effectors(self):
        return self.sd_instance.rawEffectors()

    @staticmethod
    def local_ip():
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)

    def on_rssi_received(self, client, userdata, msg):
        splits = str(msg.payload).split("$")
        origin = msg.topic.split("/")[-1]
        if len(splits) >= 2:
            if len(splits) == 3:
                mac, rssi, device_id = splits
                mac = mac.lower()
                key = device_id.lower()
            else:
                mac, rssi = splits
                mac = mac.lower()[2:]
                key = mac
            if origin not in self.log_nodes_dict:
                self.log_nodes_dict.update({origin:[]})
            self.log_nodes_dict.get(origin).insert(0, datetime.datetime.now())

            # 'fa:03:63:cb:09:03'
            possible_devs = ['fa:03:63:cb:09:03']
            if abs(int(rssi[:-1])) < 65 and key not in possible_devs:
                pass
            # checking that it actually exists
            if key in self.devices_dict:
                # checking that node exists
                if origin in [node.mac.replace("\n", "").lower() for node in self.anchors()]:
                    rssi = rssi[:-1]    # removing \n added by c++ code to have char*
                    # finally adding rssi
                    try:
                        rssi = int(rssi)
                        self.devices_dict[key][origin].append({"timestamp": datetime.datetime.now(), "value": rssi})
                    except:
                        self.errorLog("Unable to parse")
                else:
                    self.log("Unknown node")
            else:
                self.log("Unknown device communicating")
        else:
            self.errorLog("Unable to split")

    def on_message(self, client, userdata, msg):
        pass

    def run_timer(self):
        while True:
            localizationTimer = LocalizationTimer(self.client, self.sd_instance, self.devices_dict, LocalizationType.NODE)
            localizationTimer.start()
            time.sleep(2)
            # TODO here it is the right place where to clean up a bit

    def device_rssi(self, idDevice):
        if idDevice in self.devices_dict:
            return self.devices_dict[idDevice]
        else:
            return None

    def __init__(self, name, id_sd = -1):
        LogThread.__init__(self, name)
        id_sd = int(id_sd)
        # Initializing architecture stuff
        parser = Parser().getInstance()
        try:
            sd_instance = parser.read_smartdirections_instance(id_sd)
        except:
            print("ERROR: wrong SD ID")
            raise Exception()
        #building = list(filter(lambda b: b.id == idBuilding, parser.read_sd_buildings()))
        #assert len(building) == 1, "Something wrong"
        self.sd_instance = sd_instance
        self.sd_instance.initRouting()

        # Initializing mqtt protocol
        self.client = mqtt.Client()
        self.client.username_pw_set(username="brain", password="brain")

        self.client.connect(BROKER_IP, 1884, 60)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # start timer executing localization thread
        t1 = threading.Thread(target=self.run_timer)
        t1.start()

    def run(self):
        self.client.loop_forever()
