'''
Simply prints when device is close (RSSI in a range of -90 to -20, being -90 = far)
'''
from pubsub.core import Publisher

from ble.publisher import MQTTPublisher


def proximity_callback(bt_addr, rssi, packet, additional_info):
    if "62:74:aa:d4:b2:c7" in bt_addr.lower():
        if abs(rssi) < 50:
            print("FILIP IS CLOSE")
    else:
        print("IT's NOT FILIP")

'''
Communicates RSSI to brain
TODO brain:
- it is NOT one of the nodes
- 1)
- collects assets from all nodes -> implement until here
- 2)
- every time t, computes localization (my algorithm? other? TODO search) for each device given info of other nodes. It may be that it won't receive them; in that case, it will provide very low RSSI by default
- 3)
- use of the information of localization
- ... and same to other devices in the place that have the capability of showing the localization
OSS: we could make a distributed system on which we have the brain among them. They are connected to WiFi. 
By doing this, we can have a better one that will work as brain, 
but if it falls down we can implement a reassignment of the node
'''
def communicate_callback(publisher: MQTTPublisher, bt_addr, rssi, packet, additional_info):
    # print("RSSI {}".format(rssi))
    publisher.publish(bt_addr, rssi)

