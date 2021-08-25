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
        return 2000
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
                client.publish(self.topic(effector).lower(), message)
    def compute(self, mac_dict, mac, origin):
        pass

class NeighboursLocalization(Localization):
    def topic(self, effector):
        return "directions/effector/neighbour/effector_{}".format(effector.idx)
    def build_messages(self, **kwargs):
        # each pair (node, device) has a message of the form: (node, device, is_close)
        nodes, devices, devices_dict = kwargs["nodes"].nodes, kwargs["devices"], kwargs["devices_dict"]
        # filtering: only in case the device is navigating we compute the localization
        active_devices = [device for device in devices if "status" in devices_dict[device] and devices_dict[device]["status"] == Status.NAVIGATING]
        messages = []
        for node, device in itertools.product(*[nodes, active_devices]):
            # check values that do not differ much in time
            anchor_id = node.idx    # before: node.mac.lower()
            if device in devices_dict and anchor_id in devices_dict[device]:
                current_vals = list(devices_dict[device][anchor_id])
                recent_values = list(map(lambda x: x["value"], filter(
                    lambda x: x["timestamp"] + datetime.timedelta(milliseconds=self.timeThreshold()) > datetime.datetime.now(),
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
        return "directions/effector/activate/effector_{}".format(effector.idx)
    def build_messages(self, **kwargs):
        # each pair (node, device) has a message of the form: (node, device, is_close)
        # effectors, nodes, devices, devices_dict = kwargs["effectors"], kwargs["nodes"], kwargs["devices"], kwargs["devices_dict"]
        sd_instance, devices, devices_dict = kwargs["sd_instance"], kwargs["devices"], kwargs["devices_dict"]

        # filtering: only in case the device is navigating we compute the localization
        active_devices = [device for device in devices if
                          "status" in devices_dict[device] and devices_dict[device]["status"] == Status.NAVIGATING]

        messages = []
        close_anchors = {}
        best_anchors = {}
        # find first each pair (device, node)
        for device_key in active_devices:
            found, best_val = False, self.rssiThreshold()
            closest_anchor = None
            for node in sd_instance.raw_anchors():
                anchor_id = node.idx    # before: node.mac.lower()
                current_vals = list(devices_dict[device_key][anchor_id])
                recent_values = list(map(lambda x: x["value"], filter(lambda x: x["timestamp"] + datetime.timedelta(milliseconds=self.timeThreshold()) > datetime.datetime.now(), current_vals)))
                rssi_val = -100
                if len(recent_values) > 0:
                    rssi_val = mean(recent_values)
                if rssi_val > best_val:
                    best_val = rssi_val
                    closest_anchor = node
            if closest_anchor is not None:
                best_anchors[device_key] = closest_anchor

        # for each device, use the closest anchor
        for device_key in best_anchors.keys():
            node = best_anchors[device_key]
            color = devices_dict[device_key]['color']
            device_building = [b for b in sd_instance.buildings if devices_dict[device_key]['id_building']==b.id][0]

            is_first_time = False
            device_destination = device_building.findPoI(devices_dict[device_key]['id_POI'])
            # only first time: last_anchor is the last encountered anchor; first_anchor is the first encountered anchor
            if 'last_anchor' not in devices_dict[device_key]:
                devices_dict[device_key]['last_anchor'] = node
            if 'first_anchor' not in devices_dict[device_key]:
                devices_dict[device_key]['first_anchor'] = node

            # this feature is currently not used.
            # if True, last_anchor is the last encountered (gets updated)
            # if False, last_anchor is the same as the first encountered
            update_last_anchor = False
            if update_last_anchor:
                if node.idx != devices_dict[device_key]['last_anchor'].idx:
                    devices_dict[device_key]['last_anchor'] = node
            device_origin = devices_dict[device_key]['last_anchor']

            # localization: node is close if threshold is greater than <rssiThreshold> and no other node is close
            effectors_to_activate, face_to_show, relative_message_to_show, absolute_message_to_show = \
                device_building.toActivate(node, device_destination, device_origin)

            from map.elements.planimetry.point_type import Direction, MessageDirection

            if not devices_dict[device_key]['shown_first']:
                face_to_show, relative_message_to_show = Direction.ALL, MessageDirection.START

            first_anchor_show_all_faces = False

            if effectors_to_activate is not None:
                if first_anchor_show_all_faces and devices_dict[device_key]['shown_first'] \
                        and node.idx == devices_dict[device_key]['first_anchor'].idx\
                        and relative_message_to_show != MessageDirection.ARRIVED:
                    faces, directions = device_building.portDirectionsToFaces(absolute_message_to_show)
                else:
                    faces, directions = [face_to_show], [relative_message_to_show]
                for face_to_show, relative_message_to_show in zip(faces, directions):
                    messages.append((effectors_to_activate, "{}$1${}${}${}".format(device_key, face_to_show, relative_message_to_show, color)))
                all_effectors = device_building.raw_effectors()
                for remaining_effector in all_effectors:
                    if remaining_effector.idx != effectors_to_activate.idx:
                        # relevant only for smartphone effectors. Masters do not show the message persistently
                        messages.append(
                            (remaining_effector, "{}$0${}${}${}".format(device_key, face_to_show, relative_message_to_show, color)))


            else:
                print("INFO: no effector to activate for device {}".format(device_key))

            devices_dict[device_key]['shown_first'] = True

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