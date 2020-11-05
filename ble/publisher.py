import paho.mqtt.client as mqtt

class MQTTPublisher:
    client: mqtt.Client
    def __init__(self):
        self.client = mqtt.Client()
        address = "localhost"
        self.client.connect(address, 1883, 120)

    def disconnect(self):
        self.client.disconnect()

    def publish(self, address, rssi, topic = "ble/rssi"):
        message = "{}:{}".format(address, rssi)
        self.client.publish(topic, message);