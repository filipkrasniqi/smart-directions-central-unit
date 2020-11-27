
import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, rc):
    # print("Connected with result code " + str(rc))
    client.subscribe("ble/rssi")

def on_message(client, userdata, msg):
    print(msg.payload)

def on_log(client, userdata, level, buf):
  print("log: ",buf)

if __name__ == "__main__":
    client = mqtt.Client()
    client.tls_set(ca_certs="../keys/mosquitto.org.crt", certfile="../keys/client.crt", keyfile="../keys/client.key")

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("test.mosquitto.org", 8884, 10)
    client.loop_forever()