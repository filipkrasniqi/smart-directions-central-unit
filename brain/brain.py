from ble.subscriber_thread import MQTTSubscriber
from utils.parser import Parser


def start():
    # initializing nodes
    data_path = "../assets/"
    parser = Parser(data_path).getInstance()
    # TODO cambiare: devo fare la read dal .pkl -> è l'intero building!!! Ne seleziono uno...
    nodes, effectors = parser.read_nodes(), parser.read_effectors()
    subscriberThread = MQTTSubscriber("MQTT", nodes, effectors)
    subscriberThread.start()

if __name__ == "__main__":
    start()