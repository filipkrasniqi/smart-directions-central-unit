from threading import Timer

from ble.log_thread import LogThread
from localization.localization import Localization, LocalizationType, LocalizationFactory
import paho.mqtt.client as mqtt

from map.elements.effector import Effectors
from map.elements.nodes import Nodes


class LocalizationTimer(LogThread):
    localization: Localization
    def set(self, localizationType: LocalizationType):
        self.localization = LocalizationFactory().getInstance().build(localizationType)
    def __init__(self, client: mqtt.Client, nodes: Nodes, effectors: Effectors, devices_dict,
                 localizationType: LocalizationType = LocalizationType.NODE):
        LogThread.__init__(self, "Localization")
        self.set(localizationType)
        self.client, self.nodes, self.effectors, self.devices_dict = client, nodes, effectors, devices_dict

    def run(self):
        # kwargs: nodes, devices, devices_dict, effectors
        devices = self.devices_dict.keys()
        self.localization.send(
            client=self.client,
            nodes=self.nodes,
            devices_dict=self.devices_dict,
            effectors=self.effectors,
            devices=devices
        )

