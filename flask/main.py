import datetime

from statistics import mean

import numpy as np
from flask import Flask, jsonify, request
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler

from ble.subscriber_thread import MQTTSubscriber
from localization.WifiLocalizer import WifiLocalizer
from map.elements.planimetry.sd_instance import SmartDirectionInstance
from utils.parser import Parser

from fingerprinting.main import getPosition
data_path = "/Users/filipkrasniqi/PycharmProjects/smartdirections/assets/smart_directions/"
app = Flask(__name__)
id_sds = {}
subscribers = {}

parser = Parser(data_path).getInstance()


def activate_sd_instance(id_sd, id_device, id_building, id_POI):
    if id_sd not in subscribers:
        subscriberThread = MQTTSubscriber("MQTT", id_sd)
        subscriberThread.start()
        subscribers[id_sd] = subscriberThread
    else:
        subscriberThread = subscribers[id_sd]
    # device gets tracked: needed to have info about anchors
    if id_device != -1 and id_device not in id_sds:
        id_sds[id_device] = id_sd
    if id_building >= 0 and id_POI >= 0:
        subscriberThread.activate_device(id_device, id_building, id_POI)

def deactivate_sd_instance(id_device):
    for subscriber in subscribers.values():
        if subscriber.has_device(id_device):
            subscriber.deactivate_device(id_device)

@app.route('/device/sd_instances', methods=['GET'])
def sd_instances_list():
    # returns list of buildings
    sd_instances = parser.read_smartdirections_instances()
    return jsonify(list(map(lambda b: {"id_sd": b.id, "name": b.name}, sd_instances)))

@app.route('/device/<id_sd>/building', methods=['GET'])
def building_list(id_sd):
    # returns list of buildings
    sd_instance = parser.read_sd_buildings(parser.read_smartdirections_instance(int(id_sd)))
    buildings = sd_instance.buildings
    return jsonify(list(map(lambda b: {"idBuilding": b.id, "name": b.name, "num_floors": b.floorsObjects.shape[0],
                                       "width": b.floorsObjects.shape[1], "height": b.floorsObjects.shape[2],
                                       "invalid_points": b.getInvalidIndices(),
                                       "id_pois": [p.idx for p in b.raw_pois()]}, buildings)))

@app.route('/device/<id_sd>/pois', methods=['GET'])
def pois_list(id_sd):
    # returns list of buildings
    sd_instance = parser.read_smartdirections_instance((int(id_sd)))
    pois = sd_instance.raw_pois()
    return jsonify(list(map(lambda b: {"idPOI": b.idx, "name": b.name, 'idBuilding': b.id_building}, pois)))

@app.route('/node/<mac_node>/init', methods=['POST'])
def init_node(mac_node):

    data = request.json
    assert data is not None and data["wifi"] is not None and data["id_sd"] is not None, "Wrong parameters"
    for wifi in data["wifi"]:
        assert wifi["mac"] is not None and wifi["rssi"] is not None, "Wrong wifi info: {}".format(wifi)

    id_sd, wifi = data["id_sd"], data["wifi"]
    instance: SmartDirectionInstance = parser.read_smartdirections_instance(id_sd)

    to_return = instance.add_node(mac_node.replace("\n", ""), wifi)
    return to_return

@app.route('/effector/<mac_effector>/init', methods=['POST'])
def init_effector(mac_effector):

    data = request.json
    assert data is not None and data["wifi"] is not None and data["id_sd"] is not None, "Wrong parameters"
    for wifi in data["wifi"]:
        assert wifi["mac"] is not None and wifi["rssi"] is not None, "Wrong wifi info: {}".format(wifi)

    id_sd, wifi = data["id_sd"], data["wifi"]
    instance: SmartDirectionInstance = parser.read_smartdirections_instance(id_sd)

    to_return = instance.add_effector(mac_effector.replace("\n", ""), wifi)
    return to_return

@app.route('/node/<mac_node>/ping', methods=['POST'])
def ping_from_node(mac_node):
    return "OK"

@app.route('/effector/<mac_node>/ping', methods=['POST'])
def ping_from_effector(mac_node):
    return "OK"

@app.route('/device/<id_device>/activate', methods=['POST'])
def select_sd_instance(id_device):
    data = request.json
    assert data is not None and data["id_sd"] is not None and data["id_POI"] is not None and data["id_building"] is not None, "Wrong parameters"
    activate_sd_instance(data["id_sd"], id_device, data["id_building"],data["id_POI"])
    return "OK"

@app.route('/device/<id_device>/deactivate', methods=['POST'])
def deactivate_device(id_device):
    deactivate_sd_instance(id_device)
    return "OK"

@app.route('/device/<id_device>/save', methods=['POST'])
def save_mac_position(id_device):
    data = request.json
    assert data is not None and data["wifi"] is not None and data["id_building"] is not None and data["id_POI"] is not None and data["id_sd"] is not None and data["position"] is not None and data["position"][
        "x"] is not None and data["position"]["y"] is not None and data["position"]["z"] is not None, "Wrong parameters"
    for wifi in data["wifi"]:
        assert wifi["mac"] is not None and wifi["rssi"] is not None, "Wrong wifi info: {}".format(wifi)
    # asserted we have {wifi: [{mac: <>, rssi: <>}, ...], position: ...}
    try:
        id_sd = id_sds[id_device]
    except:
        id_sd = data['id_sd']
        # now it is useless to activate it...
        activate_sd_instance(id_sd, id_device, data['id_building'], data['id_POI'])
    subscriberThread = subscribers[id_sd]
    ble = subscriberThread.device_rssi(id_device)
    parser.save_wifi_rssi(id_sd, data["id_building"], data["wifi"], data["position"], ble, also_ble=False)
    return jsonify({})


@app.route('/device/<id_device>/locate', methods=['POST'])
def locate(id_device):
    data = request.json
    assert data is not None and data["wifi"] is not None and data["floor"] is not None and data["id_POI"] is not None and data["id_sd"] is not None and data["id_building"] is not None, "Wrong parameters"
    for wifi in data["wifi"]:
        assert wifi["mac"] is not None and wifi["rssi"] is not None, "Wrong wifi info: {}".format(wifi)
    # asserted we have {wifi: [{mac: <>, rssi: <>}, ...], position: ...}
    try:
        id_sd = id_sds[id_device]
    except:
        id_sd = data['id_sd']
        # now it is useless to activate it...
        activate_sd_instance(id_sd, id_device, data['id_building'], data['id_POI'])

    sd_instance = parser.read_smartdirections_instance(id_sd)
    wf_localizer = WifiLocalizer(sd_instance)
    id_building = wf_localizer.infer_building(data['wifi'], [], False)
    floor = wf_localizer.infer_floor(data['wifi'], [], id_building, False)
    position_in_grid = wf_localizer.infer_position(data['wifi'], [], id_building, False)
    x_intervals, y_intervals = wf_localizer.get_intervals(id_building)

    return jsonify({"position": position_in_grid.item(), 'id_building': id_building.item(), 'floor' : floor.item(), 'x_intervals': x_intervals, 'y_intervals': y_intervals})


if __name__ == "__main__":
    force_clean = False
    sd_instances = parser.read_smartdirections_instances()

    if force_clean:
        id_sds_to_clean = [0, 1]
        sd_instances_to_clean = [s for s in sd_instances if s.id in id_sds_to_clean]
        for sd_instance in sd_instances_to_clean:
            parser.clean_anchors(sd_instance)
    sd_instances_to_execute = [5]
    for sd_instance in sd_instances:
        if sd_instance.id in sd_instances_to_execute:
            activate_sd_instance(sd_instance.id, id_device=-1, id_building=-1, id_POI=-1)
    app.run()
