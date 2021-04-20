import datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier

from map.elements.planimetry.building import Building
from utils.parser import Parser
from statistics import mean


class WifiLocalizer:
    def __init__(self, sd_instance, model_name='kb', name='wifi_ble'):
        self.parser = Parser().getInstance()
        self.model_name, self.name = model_name, name
        self.sd_instance = sd_instance
        self.id_sd = self.sd_instance.id

        try:
            self.model_predict_building = self.parser.load_sd_model(self.id_sd)
        except:
            print("WARNING: init SD model from scratch")
            self.model_predict_building = self.__train_sd_model(True)

        try:
            self.models_building_floor = self.parser.load_building_floor_models(self.id_sd)
        except:
            print("WARNING: init building models from scratch")
            self.models_building_floor = {b.id: self.__train_building_floor_model(b.id, True) for b in self.sd_instance.buildings}

        try:
            self.models_building = self.parser.load_building_models(self.id_sd)
        except:
            print("WARNING: init building models from scratch")
            self.models_building = self.__train_all_building_models(True)

    def __create_model(self):
        if self.model_name == 'kb':
            model = KNeighborsClassifier(n_neighbors=5)
        elif self.model_name == 'linear':
            model = LogisticRegression()
        elif self.model_name == 'nb':
            model = GaussianNB()
        else:
            raise Exception()
        return model

    def __train_building_floor_model(self, id_building, do_cv = False):
        df = self.parser.read_df_building(self.id_sd, id_building)
        model = self.__create_model()
        X = df[[col for col in df.columns if "wifi" in col or ("ble" in col and "rndm" not in col)]]
        X_fill = X.fillna(-120)

        y = df['z']

        if do_cv:
            self.do_cv(model, X_fill, y, 'building')

        model.fit(X_fill, y)
        self.parser.save_building_floor_model(self.id_sd, id_building, self.model_name, self.name, model)
        return model

    def __train_all_building_models(self, do_cv = False):
        models = {b.id: self.__train_building_model(b.id, do_cv) for b in self.sd_instance.buildings}
        return models

    def __train_building_model(self, id_building, do_cv = False):
        df = self.parser.read_df_building(self.id_sd, id_building)
        model = self.__create_model()

        building: Building = self.sd_instance.get_building_from_id(id_building)
        min_z, max_z = building.getFloorRange()
        models = []
        for z in range(min_z, max_z):
            X = df[[col for col in df.columns if "wifi" in col or ("ble" in col and "rndm" not in col)]]
            X_fill = X.fillna(-120)

            df['label'] = df.apply(lambda row: self.__get_position(row['x'], row['y'], id_building), axis=1)
            y = df['label']

            if do_cv:
                self.do_cv(model, X_fill, y, 'building')

            model.fit(X_fill, y)
            self.parser.save_building_model(self.id_sd, id_building, z, self.model_name, self.name, model)
            models.append(model)
        return model

    def __train_sd_model(self, do_cv = False):
        df = self.parser.read_df_sd(self.sd_instance)
        model = self.__create_model()
        X = df[[col for col in df.columns if "wifi" in col or ("ble" in col and "rndm" not in col)]]
        X_fill = X.fillna(-120)
        y = df['id_building']

        if do_cv:
            self.do_cv(model, X_fill, y, 'building')

        model.fit(X_fill, y)
        self.parser.save_sd_model(self.id_sd, self.model_name, self.name, model)
        return model

    def do_cv(self, model, X, y, name, k=5):
        splits_x, splits_y = [], []
        for i in range(k):
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33)
            splits_x.append((X_train, X_test))
            splits_y.append((y_train, y_test))

        scores = []
        for i in range(k):
            X_train, X_test = splits_x[i]
            y_train, y_test = splits_y[i]
            model.fit(X_train, y_train)
            scores.append(model.score(X_test, y_test))
        print("CNN SCORE for {} -> {}".format(name, mean(scores)))

    def __get_position(self, x, y, id_building):#min_x = 0, max_x = 12, min_y = 0, max_y = 14):
        x_intervals, y_intervals = self.get_intervals(id_building)

        x_block = [i for i, interval in enumerate(x_intervals) if interval[0] <= x <= interval[1]][0]
        y_block = [i for i, interval in enumerate(y_intervals) if interval[0] <= y <= interval[1]][0]

        return x_block + y_block * len(x_intervals)

    def get_intervals(self, id_building):
        building: Building = self.sd_instance.get_building_from_id(id_building)
        x_intervals = building.horizontal_grid_intervals()
        y_intervals = building.vertical_grid_intervals()

        return x_intervals, y_intervals

    def infer_floor(self, wifi_features, ble_features, id_building, also_ble = True):
        model = self.models_building_floor[id_building]
        df = self.parser.read_df_sd(self.sd_instance)
        features = WifiLocalizer.build_features(df, wifi_features, ble_features, also_ble)
        id_building = model.predict(np.array(features).reshape(1, -1))
        return id_building[0]

    def infer_building(self, wifi_features, ble_features, also_ble = True):
        model = self.model_predict_building
        df = self.parser.read_df_sd(self.sd_instance)
        features = WifiLocalizer.build_features(df, wifi_features, ble_features, also_ble)
        id_building = model.predict(np.array(features).reshape(1, -1))
        return id_building[0]

    def infer_position(self, wifi_features, ble_features, id_building, floor, also_ble = True):
        model = self.models_building[id_building]
        df = self.parser.read_df_building(self.id_sd, id_building)
        features = WifiLocalizer.build_features(df, wifi_features, ble_features, also_ble)
        position = model.predict(np.array(features).reshape(1, -1))
        return position[0]

    @staticmethod
    def build_features(df, wifi_features, ble_features, also_ble = True):
        wifi_cols = [col for col in df.columns if "wifi" in col]

        features = []
        for wifi_col in wifi_cols:
            rssi_vals = [wifi['rssi'] for wifi in wifi_features if "wifi_{}".format(wifi['mac']) == wifi_col]
            rssi = -120
            if len(rssi_vals) > 0:
                rssi = rssi_vals[0]
            features.append(rssi)
        if also_ble:
            ble_cols = [col for col in df.columns if "ble" in col and "rndm" not in col]
            for ble_col in ble_cols:
                TIME_THRESHOLD = 3  # 3 seconds of threshold: if the difference is higher I don't take them
                ble_mac = ble_col.split("_")[1]
                recent_values = [b_val["value"] for b_val in ble_features[ble_mac]
                                 if b_val["timestamp"] + datetime.timedelta(0, seconds=TIME_THRESHOLD) >
                                 datetime.datetime.now()]
                if len(recent_values) <= 0:
                    recent_values = [-100]
                features.append(mean(recent_values))
        return features