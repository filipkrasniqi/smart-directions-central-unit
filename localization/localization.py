import itertools
from enum import Enum
import datetime
from statistics import mean

import paho.mqtt.client as mqtt

'''
Singleton instanced as such to apply a localization that depends on the mode.
It will compute the position and communicate it accordingly.
'''
class Localization:

    def rssiThreshold(self):
        return -65
    def timeThreshold(self):
        return 5  # 10s expressed in ms
    def getType(self):
        pass
    def topic(self):
        pass
    def build_messages(self, **kwargs):
        pass
    def send(self, **kwargs):
        client = kwargs["client"]
        for message in self.build_messages(**kwargs):
            client.publish(self.topic(), message)
    def compute(self, mac_dict, mac, origin):
        pass

class NeighboursLocalization(Localization):
    def topic(self):
        return "ble/neighbours"
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
            messages.append("{}${}${}".format(node.mac, device, close))
        return messages
    def getType(self):
        return LocalizationType.NEIGHBOURS

class NodeLocalization(Localization):
    def topic(self):
        return "ble/effectors/activate"
    def build_messages(self, **kwargs):
        # each pair (node, device) has a message of the form: (node, device, is_close)
        effectors, nodes, devices, devices_dict = kwargs["effectors"], kwargs["nodes"].nodes, kwargs["devices"], kwargs["devices_dict"]
        # filtering: only in case the device is navigating we compute the localization
        active_devices = [device for device in devices if
                          "status" in devices_dict[device] and devices_dict[device]["status"] == Status.NAVIGATING]
        messages = []
        for node, device in itertools.product(*[nodes, active_devices]):
            # check values that do not differ much in time
            if device in devices_dict and node.mac in devices_dict[device]:
                current_vals = list(devices_dict[device][node.mac])
                recent_values = list(map(lambda x: x["value"], filter(lambda x: x["timestamp"] + datetime.timedelta(0, self.timeThreshold()) > datetime.datetime.now(), current_vals)))
            else:
                recent_values = []
            # localization: node is close if threshold is greater than <rssiThreshold>
            close = 1 if len(recent_values) > 0 and mean(recent_values) > self.rssiThreshold() else 0
            # then, we activate the effectors that are close to it
            effectors_to_activate = effectors.activate_effectors(node)
            for effector in effectors_to_activate:
                messages.append("{}${}${}".format(effector.mac, device, close))
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