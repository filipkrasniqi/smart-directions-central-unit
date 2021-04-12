from ble.subscriber_thread import MQTTSubscriber
from utils.parser import Parser


def start():
    # initializing nodes
    parser = Parser().getInstance()
    id_sd = 0
    sd_instance = parser.read_smartdirections_instance(id_sd)
    subscriberThread = MQTTSubscriber("MQTT", sd_instance.id)
    subscriberThread.start()

if __name__ == "__main__":
    start()