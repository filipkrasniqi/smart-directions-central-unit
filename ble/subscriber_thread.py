import collections
import socket

import paho.mqtt.client as mqtt
from ble.log_thread import LogThread

BROKER_IP = "54.164.129.181";#"192.168.1.151" # my laptop

class MQTTSubscriber(LogThread):
    client: mqtt.Client
    mac_dict = {}   # dictionary of the form: {mac: {origin: <rssi_queue>}}, being mac = <device sniffed>, origin = <sniffer> (rberry pi)
    QUEUE_LENGTH = 5

    def on_connect(self, client, userdata, flags, rc):
        # print("Connected with result code " + str(rc))
        client.subscribe("ble/rssi")

    @staticmethod
    def local_ip():
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)

    def on_message(self, client, userdata, msg):
        splits = str(msg.payload).split("$")
        if len(splits) >= 3:
            origin, mac, rssi = splits
            rssi = rssi[:-1]    # removing \n added by c++ code to have char*
            if mac not in self.mac_dict:
                self.mac_dict[mac] = {}
            if origin not in self.mac_dict[mac]:
                self.mac_dict[mac][origin] = collections.deque(self.QUEUE_LENGTH * [-100], self.QUEUE_LENGTH)  # by default they are set to 0
            try:
                rssi = int(rssi)
                self.mac_dict[mac][origin].append(rssi)
                close = 1 if (sum(list(self.mac_dict[mac][origin])) / len(self.mac_dict[mac][origin])) > -80 else 0
                if close:
                    print("ON MESSAGE: {}".format(mac))
                message = "{}${}${}".format(origin, mac, close)
                self.client.publish("ble/neighbours", message)
            except:
                print("ERROR: was not able to parse")
        else:
            print("ERROR: was not able to split")



    def __init__(self, name):
        LogThread.__init__(self, name)
        self.name = name

        self.client = mqtt.Client()
        self.client.username_pw_set("test", "password123")
        self.client.connect(BROKER_IP, 1883, 60)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def run(self):
        self.client.loop_forever()
