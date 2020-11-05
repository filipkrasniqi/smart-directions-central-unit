from ble.subscriber_thread import MQTTSubscriber

if __name__ == "__main__":
    subscriberThread = MQTTSubscriber("MQTT")
    subscriberThread.start()