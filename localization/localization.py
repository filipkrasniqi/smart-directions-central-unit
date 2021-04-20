import itertools
from enum import Enum
import datetime
from statistics import mean

import paho.mqtt.client as mqtt

from map.elements.effector import Effector

'''
Singleton instanced as such to apply a localization that depends on the mode.
It will compute the position and communicate it accordingly.
'''
class Localization:

    def rssiThreshold(self):
        return -65
    def timeThreshold(self):
        return 3000  # 10s expressed in ms
    def getType(self):
        pass
    def topic(self, effector: Effector):
        pass
    def build_messages(self, **kwargs):
        pass
    def send(self, **kwargs):
        client = kwargs["client"]
        for effectorMessage in self.build_messages(**kwargs):
            effector, message = effectorMessage
            if effector:
                client.publish(self.topic(effector), message)
    def compute(self, mac_dict, mac, origin):
        pass

class NeighboursLocalization(Localization):
    def topic(self, effector):
        return "directions/effector/neighbour/{}".format(effector.mac)
    def build_messages(self, **kwargs):
        # each pair (node, device) has a message of the form: (node, device, is_close)
        nodes, devices, devices_dict = kwargs["nodes"].nodes, kwargs["devices"], kwargs["devices_dict"]
        # filtering: only in case the device is navigating we compute the localization
        active_devices = [device for device in devices if "status" in devices_dict[device] and devices_dict[device]["status"] == Status.NAVIGATING]
        messages = []
        for node, device in itertools.product(*[nodes, active_devices]):
            # check values that do not differ much in time
            if device in devices_dict and node.mac in devices_dict[device]:
                current_vals = list(devices_dict[device][node.mac])
                recent_values = list(map(lambda x: x["value"], filter(
                    lambda x: x["timestamp"] + datetime.timedelta(0, self.timeThreshold()) > datetime.datetime.now(),
                    current_vals)))
            else:
                recent_values = []
            # localization: node is close if threshold is greater than <rssiThreshold>
            close = 1 if len(recent_values) > 0 and mean(recent_values) > self.rssiThreshold() else 0
            messages.append((node, "{}${}".format(device, close)))
        return messages
    def getType(self):
        return LocalizationType.NEIGHBOURS

class NodeLocalization(Localization):
    def topic(self, effector):
        return "directions/effector/activate/{}".format(effector.mac)
    def build_messages(self, **kwargs):
        # each pair (node, device) has a message of the form: (node, device, is_close)
        # effectors, nodes, devices, devices_dict = kwargs["effectors"], kwargs["nodes"], kwargs["devices"], kwargs["devices_dict"]
        sd_instance, devices, devices_dict = kwargs["sd_instance"], kwargs["devices"], kwargs["devices_dict"]

        # TODO questo building è quello nel quale viene attivato un effettore e del quale vengono considerate le ancore; per ora, è il primo che trova
        # TODO da ora in avanti, sarà meglio avere la SD instance, nel quale vengono controllati nuovamente tutti i nodi X devices
        # TODO per quanto riguarda l'activate, non la si fa più sul building ma sul sd_instance, in modo che se si è ai margini di un building si attiva ANCHE l'effettore d'inizio del building successivo -> navigazione EXTRA BUILDINGS


        # filtering: only in case the device is navigating we compute the localization
        active_devices = [device for device in devices if
                          "status" in devices_dict[device] and devices_dict[device]["status"] == Status.NAVIGATING]

        messages = []
        close_anchors = {}
        best_anchors = {}
        # find first each pair (device, node)
        for device in active_devices:
            found, best_val = False, self.rssiThreshold()
            closest_anchor = None
            for node in sd_instance.raw_anchors():
                current_vals = list(devices_dict[device][node.mac])
                recent_values = list(map(lambda x: x["value"], filter(lambda x: x["timestamp"] + datetime.timedelta(0, self.timeThreshold()) > datetime.datetime.now(), current_vals)))
                rssi_val = -100
                if len(recent_values) > 0:
                    rssi_val = mean(recent_values)
                if rssi_val > best_val:
                    best_val = rssi_val
                    closest_anchor = node
            if closest_anchor is not None:
                best_anchors[device] = closest_anchor

        # for each device, use the closest anchor
        for device in best_anchors.keys():
            node = best_anchors[device]
            device_building = [b for b in sd_instance.buildings if devices_dict[device]['id_building']==b.id][0]

            device_destination = device_building.findPoI(devices_dict[device]['id_POI'])

            # check values that do not differ much in time
            if device in devices_dict and node.mac in devices_dict[device]:
                current_vals = list(devices_dict[device][node.mac])
                recent_values = list(map(lambda x: x["value"], filter(lambda x: x["timestamp"] + datetime.timedelta(0, self.timeThreshold()) > datetime.datetime.now(), current_vals)))
            else:
                recent_values = []
            # localization: node is close if threshold is greater than <rssiThreshold> and no other node is close
            if device in close_anchors:
                close = 0
            else:
                close = 1 if len(recent_values) > 0 and mean(recent_values) > self.rssiThreshold() else 0
            # then, we activate the effectors that are close to it
            if close:
                effectors_to_activate, face_to_show, relative_message_to_show = device_building.toActivate(node, device_destination)
                if isinstance(effectors_to_activate, list):
                    for effector in effectors_to_activate:
                        messages.append((effector, "{}${}".format(device, close)))
                else:
                    effector = effectors_to_activate
                    if effector is not None:
                        messages.append((effector, "{}$1${}${}".format(device, face_to_show, relative_message_to_show)))
                        all_effectors = device_building.raw_effectors()
                        for remaining_effector in all_effectors:
                            if remaining_effector.idx != effector:
                                messages.append(
                                    (remaining_effector, "{}$0${}${}".format(device, face_to_show, relative_message_to_show)))
                    else:
                        print("NON HO EFFETTORI DA ATTIVARE")
            else:
                pass    # must not do anything

        return messages
    def getType(self):
        return LocalizationType.NODE
'''
Factory for the localization type.
Builds depending on the enum
'''
class LocalizationFactory:
    class __LocalizationFactory:
        def __init__(self):
            pass

        def build(self, mode):
            if mode == LocalizationType.NEIGHBOURS:
                return NeighboursLocalization()
            elif mode == LocalizationType.NODE:
                return NodeLocalization()
            elif mode == LocalizationType.ACCURATE:
                raise Exception("Unsupported localization")
            else:
                raise Exception("Unexisting localization")

    __instance = None

    def __init__(self):
        if not LocalizationFactory.__instance:
            LocalizationFactory.__instance = LocalizationFactory.__LocalizationFactory()

    def __getattr__(self, name):
        return getattr(self.__instance, name)

    def getInstance(self):
        return LocalizationFactory.__instance

class LocalizationType(Enum):
    NEIGHBOURS = 1      # computes list of neighbours and communicates to all of them
    NODE = 2            # localization is done by associating to a device a node
    ACCURATE = 3        # more precise localization. TODO

class Status(Enum):
    TO_INIT = 1
    NAVIGATING = 2
    INACTIVE = 3