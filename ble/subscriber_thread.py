import collections
import socket

import paho.mqtt.client as mqtt
from ble.log_thread import LogThread

BROKER_IP = "192.168.1.151" # my laptop

class MQTTSubscriber(LogThread):
    client: mqtt.Client
    mac_dict = {}   # dictionary of the form: {mac: {origin: <rssi_queue>}}

    def on_connect(self, client, userdata, flags, rc):
        # print("Connected with result code " + str(rc))
        client.subscribe("ble/rssi")

    @staticmethod
    def local_ip():
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)

    def on_message(self, client, userdata, msg):
        # print("ON MESSAGE: {}".format(msg.payload))
        origin, mac, rssi = str(msg.payload).split("$")
        rssi = rssi[:-1]    # removing \n added by c++ code to have char*
        if mac not in self.mac_dict:
            self.mac_dict[mac] = {}
        if origin not in self.mac_dict[mac]:
            self.mac_dict[mac][origin] = collections.deque(3 * [0], 3)  # by default they are set to 0
        self.mac_dict[mac][origin].append(int(rssi))
        # TODO do something with this

    def __init__(self, name):
        LogThread.__init__(self, name)
        self.name = name

        self.client = mqtt.Client()
        self.client.connect(BROKER_IP, 1883, 60)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def run(self):
        self.client.loop_forever()
