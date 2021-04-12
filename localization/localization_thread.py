from threading import Timer

from ble.log_thread import LogThread
from localization.localization import Localization, LocalizationType, LocalizationFactory
import paho.mqtt.client as mqtt

from map.elements.effector import Effectors
from map.elements.nodes import Nodes
from map.elements.planimetry.building import Building
from map.elements.planimetry.sd_instance import SmartDirectionInstance


class LocalizationTimer(LogThread):
    localization: Localization
    def set(self, localizationType: LocalizationType):
        self.localization = LocalizationFactory().getInstance().build(localizationType)
    def __init__(self, client: mqtt.Client, sd_instance: SmartDirectionInstance, devices_dict,
                 localizationType: LocalizationType = LocalizationType.NODE):
        LogThread.__init__(self, "Localization")
        self.set(localizationType)
        self.client, self.sd_instance, self.devices_dict = client, sd_instance, devices_dict

    def run(self):
        # kwargs: nodes, devices, devices_dict, effectors
        devices = self.devices_dict.keys()
        self.localization.send(
            client=self.client,
            sd_instance=self.sd_instance,
            devices_dict=self.devices_dict,
            devices=devices
        )

