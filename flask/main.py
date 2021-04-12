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


def activate_sd_instance(id_sd, id_device):

    if id_sd not in subscribers:
        subscriberThread = MQTTSubscriber("MQTT", id_sd)
        subscriberThread.start()
        subscribers[id_sd] = subscriberThread
    else:
        subscriberThread = subscribers[id_sd]
    # device gets tracked: needed to have info about anchors
    if id_device not in id_sds:
        id_sds[id_device] = id_sd
        subscriberThread.activate_device(id_device)


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
                                       "invalid_points": b.getInvalidIndices()}, buildings)))
# TODO
@app.route('/node/<mac_node>/init/', methods=['POST'])
def init_node(mac_node):

    data = request.json
    assert data is not None and data["wifi"] is not None and data["id_sd"] is not None, "Wrong parameters"
    for wifi in data["wifi"]:
        assert wifi["mac"] is not None and wifi["rssi"] is not None, "Wrong wifi info: {}".format(wifi)

    id_sd, wifi = data["id_sd"], data["wifi"]
    instance: SmartDirectionInstance = parser.read_smartdirections_instance(id_sd)

    id_building = -1
    position = None
    assert id_building > 0 and position is not None, "Wrong values"
    instance.add_node(id_building, mac_node, wifi)
    return "OK"

@app.route('/device/<id_device>/activate/', methods=['POST'])
def select_sd_instance(id_device):
    data = request.json
    assert data is not None and data["id_sd"] is not None, "Wrong parameters"
    activate_sd_instance(data["id_sd"], id_device)
    return "OK"

@app.route('/device/<id_device>/save', methods=['POST'])
def save_mac_position(id_device):
    data = request.json
    assert data is not None and data["wifi"] is not None and data["id_building"] is not None and data["id_sd"] is not None and data["position"] is not None and data["position"][
        "x"] is not None and data["position"]["y"] is not None and data["position"]["z"] is not None, "Wrong parameters"
    for wifi in data["wifi"]:
        assert wifi["mac"] is not None and wifi["rssi"] is not None, "Wrong wifi info: {}".format(wifi)
    # asserted we have {wifi: [{mac: <>, rssi: <>}, ...], position: ...}
    try:
        id_sd = id_sds[id_device]
    except:
        id_sd = data['id_sd']
        activate_sd_instance(id_sd, id_device)
    subscriberThread = subscribers[id_sd]
    ble = subscriberThread.device_rssi(id_device)
    parser.save_wifi_rssi(id_sd, data["id_building"], data["wifi"], data["position"], ble)
    return "OK"


@app.route('/device/<id_device>/locate', methods=['POST'])
def locate(id_device):
    data = request.json
    assert data is not None and data["wifi"] is not None and data["id_sd"] is not None and data["id_building"] is not None, "Wrong parameters"
    for wifi in data["wifi"]:
        assert wifi["mac"] is not None and wifi["rssi"] is not None, "Wrong wifi info: {}".format(wifi)
    # asserted we have {wifi: [{mac: <>, rssi: <>}, ...], position: ...}
    try:
        id_sd = id_sds[id_device]
    except:
        id_sd = data['id_sd']
        activate_sd_instance(id_sd, id_device)
    subscriberThread = subscribers[id_sd]
    ble = subscriberThread.device_rssi(id_device)

    also_ble = True
    prefix_ble = ""
    if also_ble:
        prefix_ble = "_ble"
    name = "wifi" + prefix_ble

    model_name = "nb"
    # TODO prima ottenere z value
    model = parser.load_building_model(id_sd, data['id_building'], model_name, name)
    df = parser.read_df_building(id_sd, data['id_building'])
    wifi_cols = [col for col in df.columns if "wifi" in col]
    features = []
    for wifi_col in wifi_cols:
        rssi_vals = [wifi['rssi'] for wifi in data['wifi'] if "wifi_{}".format(wifi['mac']) == wifi_col]
        rssi = -120
        if len(rssi_vals) > 0:
            rssi = rssi_vals[0]
        features.append(rssi)
    if also_ble:
        ble_cols = [col for col in df.columns if "ble" in col and "rndm" not in col]
        for ble_col in ble_cols:
            TIME_THRESHOLD = 3  # 3 seconds of threshold: if the difference is higher I don't take them
            ble_mac = ble_col.split("_")[1]
            recent_values = [b_val["value"] for b_val in ble[ble_mac]
                             if b_val["timestamp"] + datetime.timedelta(0, seconds=TIME_THRESHOLD) >
                             datetime.datetime.now()]
            if len(recent_values) <= 0:
                recent_values = [-100]
            features.append(mean(recent_values))
    # TODO bisognerebbe fare una model predict anche per il building
    position = model.predict(np.array(features).reshape(1, -1))
    return jsonify({"position": int(position[0])})


if __name__ == "__main__":
    app.run()
