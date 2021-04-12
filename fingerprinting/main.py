from statistics import mean

import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegressionCV, LogisticRegression
from matplotlib import pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler

from joblib import dump, load

# TODO next step: inizializzare i nodi mettendoli nei centri delle posizioni della griglia grazie al wifi
from utils.parser import Parser


def getPosition(x, y):
    x_intervals = [(0, 4), (5, 8), (9, 12)]
    y_intervals = [(0, 4), (5, 9), (10, 14)]
    x_block = [i for i, interval in enumerate(x_intervals) if interval[0] <= x <= interval[1]][0]
    y_block = [i for i, interval in enumerate(y_intervals) if interval[0] <= y <= interval[1]][0]
    max_x_block, max_y_block = 3, 3
    # x_block, y_block = min(int(x/3), 2), min(int(y/5), 2)
    return x_block + y_block * max_x_block


if __name__ == '__main__':
    parser = Parser().getInstance()
    id_building = 1
    id_sd = 0
    floor = 0
    df = parser.read_df_building(id_sd, id_building)

    df['label'] = df.apply(lambda row: getPosition(row['x'], row['y']), axis=1)
    also_ble = True

    df['label'].plot.hist(bins=9)
    plt.show()
    if also_ble:
        X = df[[col for col in df.columns if "wifi" in col or ("ble" in col and "rndm" not in col)]]
    else:
        X = df[[col for col in df.columns if "wifi" in col]]
    X_fill = X.fillna(-120)
    # X_fill = StandardScaler().fit_transform(X_fill)
    y = df['label']
    splits_x, splits_y = [], []
    for i in range(5):
        X_train, X_test, y_train, y_test = train_test_split(X_fill, y, test_size=0.33)
        splits_x.append((X_train, X_test))
        splits_y.append((y_train, y_test))
    # CV
    scores_knn = []
    for i in range(5):
        knn_c = KNeighborsClassifier(n_neighbors=5)
        X_train, X_test = splits_x[i]
        y_train, y_test = splits_y[i]
        knn_c.fit(X_train, y_train)
        scores_knn.append(knn_c.score(X_test, y_test))
    scores_linear = []
    for i in range(5):
        linear_c = LogisticRegression()
        X_train, X_test = splits_x[i]
        y_train, y_test = splits_y[i]
        linear_c.fit(X_train, y_train)
        scores_linear.append(linear_c.score(X_test, y_test))
    scores_gnb = []
    for i in range(5):
        gnb_c = GaussianNB()
        X_train, X_test = splits_x[i]
        y_train, y_test = splits_y[i]
        gnb_c.fit(X_train, y_train)
        scores_gnb.append(gnb_c.score(X_test, y_test))
    print("SCORE KNN {}".format(mean(scores_knn)))
    print("SCORE linear {}".format(mean(scores_linear)))
    print("SCORE gnb {}".format(mean(scores_gnb)))

    prefix_ble = ""
    if also_ble:
        prefix_ble = "_ble"
    name = "wifi" + prefix_ble

    knn_c = KNeighborsClassifier(n_neighbors=5)
    knn_c.fit(X_fill, y)
    model_name = "knn"
    parser.save_building_model(id_sd, id_building, model_name, name, knn_c)

    linear_c = LogisticRegression()
    linear_c.fit(X_fill, y)
    model_name = "linear"
    parser.save_building_model(id_sd, id_building, model_name, name, linear_c)

    gnb_c = GaussianNB()
    gnb_c.fit(X_fill, y)
    model_name = "nb"
    parser.save_building_model(id_sd, id_building, model_name, name, gnb_c)

    # TODO trainare anche un modello per capire in che building è!!!
