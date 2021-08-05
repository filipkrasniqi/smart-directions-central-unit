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

BROKER_IP = "80.211.69.17"          # broker IP
INACTIVITY_MAX_TIME_MS = 30000      # max inactivity time: max time a device can stay inactive
MUTE_MAX_TIME_MS = 60000            # max mute time: max time device can be in navigating status without being found

class MQTTSubscriber(LogThread):
    client: mqtt.Client
    devices_dict = {}   # dictionary of the form: {mac: {origin: <rssi_queue>}}, being mac = <device sniffed>, origin = <sniffer> (rberry pi)
    QUEUE_LENGTH = 3
    nodes: Nodes
    effectors: Effectors
    all_devs = set()
    log_nodes_dict = {} # for log purposes: shows last communication timestamp for each node
    distinct_colors = [0, 1, 2, 3]
    colors_dict = {}    # maps each destination with distinct color

    def on_connect(self, client, userdata, flags, rc):
        self.client.subscribe("directions/anchor/proximity/#")
        self.client.subscribe("directions/device/activate/#")
        self.client.subscribe("directions/device/deactivate/#")
        self.client.message_callback_add('directions/anchor/proximity/#', self.on_rssi_received)
        self.client.message_callback_add('directions/device/activate/#', self.on_activate)
        self.client.message_callback_add('directions/device/deactivate/#', self.on_deactivate)

    def on_activate(self, client, userdata, msg):
        id_POI, id_building, key = msg.payload.decode('utf-8').split("$")
        self.activate_device(key, int(id_building), int(id_POI))

    def activate_device(self, key, id_building, id_POI):
        current_time = datetime.datetime.now()
        if key not in self.devices_dict:
            self.devices_dict[key] = {}
        for origin in self.anchors():
            if origin.mac not in self.devices_dict[key]:
                mac_anchor = origin.mac.replace("\n", "").lower()
                self.devices_dict[key][mac_anchor] = collections.deque(self.QUEUE_LENGTH * [{"timestamp": current_time, "value": -100}], self.QUEUE_LENGTH)
        self.devices_dict[key]["status"] = Status.NAVIGATING
        self.devices_dict[key]['time_active'] = current_time
        self.devices_dict[key]['id_building'] = id_building
        self.devices_dict[key]['id_POI'] = id_POI
        self.devices_dict[key]['shown_first'] = False
        # assign color for that destination
        # if all colors has been assigned, can't do much: we go back (so we do %)
        # if for that destination no color has been assigned, it adds to colors_dict by taking first available colors
        #  among those that are still navigating
        if id_POI not in self.colors_dict:
            assigned_colors = [device['color'] for device in self.devices_dict.keys()
                               if 'color' in device and self.devices_dict[key]["status"] == Status.NAVIGATING]
            if len(assigned_colors) <= 0:
                to_assign_color = 0
            else:
                to_assign_color = (max(assigned_colors)+1)%len(self.distinct_colors)
            self.colors_dict[id_POI] = to_assign_color
        # we know for sure for that destination a color has been defined: we assign it to the user
        self.devices_dict[key]['color'] = self.colors_dict[id_POI]

    def on_deactivate(self, client, userdata, msg):
        key = msg.topic.split("/")[-1].lower()
        self.deactivate_device(key)

    def deactivate_device(self, device_id):
        if self.has_device(device_id):
            self.devices_dict[device_id]["status"] = Status.INACTIVE
            self.devices_dict[device_id]["time_inactive"] = datetime.datetime.now()
            self.log("{} deactivated!".format(device_id))
        else:
            self.log("WARNING: no such device: {}".format(device_id))

    def has_device(self, device_id):
        return device_id in self.devices_dict

    def anchors(self):
        return self.sd_instance.raw_anchors()

    def effectors(self):
        return self.sd_instance.raw_effectors()

    @staticmethod
    def local_ip():
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)

    def on_rssi_received(self, client, userdata, msg):
        splits = str(msg.payload).split("$")
        origin = msg.topic.split("/")[-1]
        if len(splits) >= 3:
            if len(splits) == 4:
                mac, rssi, timestamp, device_id = splits
                mac = mac.lower()
                device_id = device_id[:-1] # removing \n added by c++ code to have char*
                key = device_id.lower()
            else:
                mac, rssi, timestamp = splits
                mac = mac.lower()[2:]
                timestamp = timestamp[:-1] # removing \n added by c++ code to have char*
                key = mac
            if origin not in self.log_nodes_dict:
                self.log_nodes_dict.update({origin:[]})
            self.log_nodes_dict.get(origin).insert(0, datetime.datetime.now())

            # 'fa:03:63:cb:09:03'
            possible_devs = ['fa:03:63:cb:09:03']
            sensor_time = datetime.datetime.fromtimestamp(int(timestamp))
            # checking that it actually exists
            if key in self.devices_dict:
                # checking that node exists
                if origin in [node.mac.replace("\n", "").lower() for node in self.anchors()]:
                    origin = origin.lower()
                    # finally adding rssi
                    try:
                        rssi = int(rssi)
                        self.devices_dict[key][origin].append({"timestamp": sensor_time, "value": rssi})
                        self.devices_dict[key]["time_active"] = sensor_time
                    except:
                        self.errorLog("Unable to parse")
                else:
                    self.log("Unknown node")
            else:
                pass
                #self.log("Unknown device communicating")
                # TODO I could exploit this to tell the device to reset
        else:
            self.errorLog("Unable to split")

    def on_message(self, client, userdata, msg):
        pass

    def run_timer(self):
        while True:
            try:
                localizationTimer = LocalizationTimer(self.client, self.sd_instance, self.devices_dict, LocalizationType.NODE)
                localizationTimer.start()
                time.sleep(0.5)
                # clean up a bit
                keys = list(self.devices_dict.keys())
                i = 0
                while i < len(keys):
                    key = keys[i]
                    if self.devices_dict[key]["status"] == Status.INACTIVE and "time_inactive" in self.devices_dict[key] and\
                            self.devices_dict[key]["time_inactive"] + datetime.timedelta(milliseconds=INACTIVITY_MAX_TIME_MS) \
                            < datetime.datetime.now():
                        self.devices_dict.pop(key)
                        self.log("Deleted inactive device: {}".format(key))
                    if self.devices_dict[key]["status"] == Status.NAVIGATING and "time_active" in self.devices_dict[key] and\
                            self.devices_dict[key]["time_active"] + datetime.timedelta(milliseconds=MUTE_MAX_TIME_MS)\
                            < datetime.datetime.now():
                        self.devices_dict.pop(key)
                        self.log("Deleted mute device: {}".format(key))
                    i += 1
            except:
                self.log("WARNING: something wrong during deleting")


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
