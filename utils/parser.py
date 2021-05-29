import datetime
import os
from collections import defaultdict
from os.path import join
from statistics import mean

from joblib import dump, load

from map.elements.effector import Effectors, Effector
from map.elements.node import Node
from map.elements.nodes import Nodes
import re
import pickle
import pandas as pd

import shutil

from map.elements.planimetry.building import Building
from map.elements.planimetry.point import Point3D

class Parser:
    class __Parser:
        def __init__(self, data_dir):
            self.data_dir = data_dir
            try:
                os.makedirs(self.data_dir)
            except:
                pass

        '''
        Read so far updated buildings
        '''

        def read_buildings(self, sd_instance):
            assert sd_instance is not None, "Wrong call of read buildings"
            try:
                with open("{}buildings.pkl".format(self.data_dir), 'rb') as file:
                    buildings = pickle.load(file)
            except:
                buildings = []
            return buildings

        '''
        Read SD instances
        '''
        def read_smartdirections_instances(self):
            try:
                with open("{}sds.pkl".format(self.data_dir), 'rb') as file:
                    sd_instances = pickle.load(file)
            except:
                sd_instances = []
            return sd_instances

        def clean_anchors(self, sd_instance):
            sd_instance = self.read_sd_buildings(sd_instance)
            sd_instance.clean_anchors()
            self.write_sd_buildings(sd_instance)
        '''
        Get SmartDirection instance from ID
        '''
        def read_smartdirections_instance(self, id_sd):
            instances = Parser().getInstance().read_smartdirections_instances()
            instance = [i for i in instances if i.id == id_sd][0]
            return self.read_sd_buildings(instance)

        '''
        Writes the actual Smart Direction instance (buildings) in the directory
        '''
        def write_sd_buildings(self, sd):
            path_sd = join(self.data_dir, "sd_{}".format(sd.id))
            try:
                os.makedirs(path_sd)
            except:
                pass
            with open(join(path_sd, "buildings.pkl"), 'wb') as file:
                pickle.dump(sd.buildings, file)

        '''
        Read from file actual sd instance buildings
        '''
        def read_sd_buildings(self, sd):
            from map.elements.planimetry.sd_instance import SmartDirectionInstance
            path_sd = join(self.data_dir, "sd_{}".format(sd.id))
            try:
                with open(join(path_sd, "buildings.pkl"), 'rb') as file:
                    buildings = pickle.load(file)
                    sd_instance = SmartDirectionInstance(sd.id, buildings, sd.name)
            except:
                sd_instance = SmartDirectionInstance(sd.id, [], sd.name)
            return sd_instance

        '''
        Clears directory of a SD instance
        '''
        def clear_sd(self, sd):
            path_sd = join(self.data_dir, "sd_{}".format(sd.id))
            try:
                shutil.rmtree(path_sd)
            except:
                print("Warning: error during delete")

        '''
        Update SD instances list. In the list, we only have the wrapper info (name + id)
        '''
        def write_sd_instances(self, sds_instances):
            with open("{}sds.pkl".format(self.data_dir), 'wb') as file:
                pickle.dump(sds_instances, file)

        def path_sd(self, id_sd):
            id_sd = str(id_sd)
            path_sd = join(self.data_dir, "sd_{}".format(id_sd))
            path_wifi = join(path_sd, "wifi")
            try:
                os.makedirs(path_wifi)
            except:
                pass
            return "{}/".format(path_wifi)

        def path_building(self, id_sd, id_building):
            id_building = str(id_building)
            path_sd = self.path_sd(id_sd)
            path_dataset = join(path_sd, "wifi", id_building)
            try:
                os.makedirs(path_dataset)
            except:
                pass
            return "{}/".format(path_dataset)

        def get_filename_dataset_wifi(self, id_sd, id_building):
            path_dataset = self.path_building(id_sd, id_building)
            return "{}wifi_{}.csv".format(path_dataset, id_building)

        def get_filename_building_floor_model(self, id_sd, id_building, model, name):
            path_dataset = self.path_building(id_sd, id_building)
            return "{}floor_model_{}_{}_{}.joblib".format(path_dataset, id_building, model, name)

        def get_filename_building_model(self, id_sd, id_building, z, model, name):
            path_dataset = self.path_building(id_sd, id_building)
            return "{}model_building_{}_floor_{}_{}_{}.joblib".format(path_dataset, id_building, z, model, name)

        def get_filename_sd_model(self, id_sd, model, name):
            path_sd = self.path_sd(id_sd)
            return "{}model_{}_{}.joblib".format(path_sd, model, name)

        def save_wifi_rssi(self, id_sd, id_building, wifi, position, ble, also_ble=False):
            path_dataset = self.get_filename_dataset_wifi(id_sd, id_building)
            df = self.read_df_building(id_sd, id_building)
            df_dict = df.reset_index().to_dict('records')
            to_add = {"wifi_{}".format(wf["mac"]): wf["rssi"] for wf in wifi}
            to_add['x'] = position["x"]
            to_add['y'] = position["y"]
            to_add['z'] = position["z"]
            to_add['id_building'] = id_building

            if also_ble:
                # add the ble info
                for node_mac_address in ble:
                    if node_mac_address != "status" and "rndm" not in node_mac_address:
                        TIME_THRESHOLD = 3  # 3 seconds of threshold: if the difference is higher I don't take them
                        recent_values = [b_val["value"] for b_val in ble[node_mac_address]
                                         if b_val["timestamp"] + datetime.timedelta(0, seconds=TIME_THRESHOLD) >
                                         datetime.datetime.now()]
                        if len(recent_values) <= 0:
                            recent_values = [-100]
                        to_add["ble_{}".format(node_mac_address)] = mean(recent_values)
            to_add['date'] = pd.to_datetime("today")
            df_dict.append(to_add)
            df = pd.DataFrame(df_dict)
            df.set_index('date', inplace=True)
            df.to_csv(path_dataset)

        def read_df_building(self, id_sd, id_building):
            path_dataset = self.get_filename_dataset_wifi(id_sd, id_building)
            try:
                df = pd.read_csv(path_dataset)
            except:
                df = pd.DataFrame()
            try:
                df.set_index('date', inplace=True)
            except:
                pass    # if dataset is empty
            return df

        def read_df_sd(self, sd_instance):
            df = pd.concat([self.read_df_building(sd_instance.id, b.id) for b in sd_instance.buildings])
            return df

        def save_building_floor_model(self, id_sd, id_building, model_name, name, model):
            path_model = self.get_filename_building_floor_model(id_sd, id_building, model_name, name)
            dump(model, path_model)

        def save_building_model(self, id_sd, id_building, z, model_name, name, model):
            path_model = self.get_filename_building_model(id_sd, id_building, z, model_name, name)
            dump(model, path_model)

        def load_building_model(self, id_sd, id_building, z, model, name):
            path_model = self.get_filename_building_model(id_sd, id_building, z, model, name)
            return load(path_model)

        def load_building_floor_model(self, id_sd, id_building, model, name):
            path_model = self.get_filename_building_floor_model(id_sd, id_building, model, name)
            return load(path_model)

        def load_building_models(self, id_sd, model, name):
            from map.elements.planimetry.sd_instance import SmartDirectionInstance
            sd_instance: SmartDirectionInstance = self.read_smartdirections_instance(id_sd)
            models = {}
            for b in sd_instance.buildings:
                min_z, max_z = b.getFloorRange()
                models_building = {}
                for z in range(min_z, max_z):
                    models_building.update({z: self.load_building_model(id_sd, b.id, z, model, name)})
                models.update({b.id: models_building})

            return models

        def load_building_floor_models(self, id_sd, model, name):
            from map.elements.planimetry.sd_instance import SmartDirectionInstance
            sd_instance: SmartDirectionInstance = self.read_smartdirections_instance(id_sd)
            return {b.id: self.load_building_floor_model(id_sd, b.id, model, name) for b in sd_instance.buildings}

        def save_sd_model(self, id_sd, model_name, name, model):
            path_model = self.get_filename_sd_model(id_sd, model_name, name)
            dump(model, path_model)

        def load_sd_model(self, id_sd, model, name):
            path_model = self.get_filename_sd_model(id_sd, model, name)
            return load(path_model)

        '''
        Loads the 3D points associated to a building with discrimination of indoor and outdoor
        '''
        def read_points_from_txt(self, file_path=None, f=None, floors=None):
            assert file_path is not None or f is not None, "No file"
            if f is None:
                # file_path = "{}{}".format(file_path, "map-v1/points.txt")
                f = open(file_path, 'r')
            lines = f.readlines()
            points: list[Point3D] = []
            # parse the file to have list of x, y, z vals
            for line in lines:
                vals = line.split(",")
                x, y, z = float(vals[0]), float(vals[1]), float(vals[2])
                r, g, b = 0, 0, 0
                if len(vals) > 3:
                    r, g, b = int(vals[3]), int(vals[4]), int(
                        vals[5])
                isIndoor = (r == 255)
                if floors is None or z in floors:
                    isLectureRoom, isWideArea, isHallway, isStair, isToilet, isLift = \
                        (g == 0), (g == 30), (g == 60), (g == 90), (g == 120), (g == 150)
                else:
                    # here we have for sure a stair point, as the floors were defined and z is not in floors
                    isLectureRoom, isWideArea, isHallway, isStair, isToilet, isLift = \
                        False, False, False, True, False, False
                # we are currently not using all these info: only stair and indoor
                # TODO it would be great to cluster the rooms and init them with a PoI
                points.append(
                    Point3D.buildPoint(x, y, z, isIndoor, isLectureRoom, isWideArea, isHallway, isStair, isToilet,
                                       isLift))
            return points

        def read_floors_z(self, file_path):
            f = open(file_path, 'r')
            lines = f.readlines()
            z_vals = []
            # parse the file to have list of x, y, z vals
            for line in lines:
                vals = line.split(",")
                z_vals.append(float(vals[2]))
            return z_vals

        def parse_node(self, idx, node):
            # splits = node.split(r'\t+')
            splits = list(filter(lambda x: x != "", node.replace("\n", "").split(" ")))
            assert len(splits) == 4, "Wrong init of node"
            return Node(idx, float(splits[0]), float(splits[1]), splits[2], splits[3])

        def parse_effector(self, idx, effector):
            splits = list(filter(lambda x: x != "", effector.replace("\n", "").split(" ")))
            assert len(splits) == 4, "Wrong init of effector"
            return Effector(idx, float(splits[0]), float(splits[1]), splits[2], splits[3])

        def read_nodes(self):
            nodes = []
            with open(self.data_dir + "nodes.txt", "r") as nodes_data:
                for i, data in enumerate(nodes_data):
                    if i > 0:
                        nodes.append(self.parse_node(i, data))
                    else:
                        num_nodes = int(data.replace("\n", ""))
            adjacency = {}
            with open(self.data_dir + "adjacency.txt", "r") as adjacency_matrix:
                # saving adjacency as dictionary
                for i, adjacency_row in enumerate(adjacency_matrix):
                    adjacency[i] = []
                    for j, val in enumerate(adjacency_row.split(r'\t+')):
                        if val == "1":
                            adjacency[i].append(j)
            return Nodes(nodes, adjacency)

        def read_effectors(self):
            effectors = []
            with open(self.data_dir + "effectors.txt", "r") as effectors_data:
                for i, data in enumerate(effectors_data):
                    if i > 0:
                        effectors.append(self.parse_effector(i, data))
                    else:
                        num_effectors = int(data.replace("\n", ""))
            return Effectors(effectors)

    __instance = None

    def __init__(self, data_dir=None):
        if not Parser.__instance:
            if data_dir is None:
                print("WARNING: data dir was none")
                data_dir = "/Users/filipkrasniqi/PycharmProjects/smartdirections/assets/smart_directions/"
            Parser.__instance = Parser.__Parser(data_dir)
        else:
            if data_dir is not None:
                Parser.__instance.data_dir = data_dir

    def __getattr__(self, name):
        return getattr(self.__instance, name)

    def getInstance(self):
        return Parser.__instance
